"""实体变更审批领域服务：管理实体模型变更单的起草、提交审批、生效与驳回。

数据链路位置：模型治理层流程端，负责消费实体定义的版本变更，
把生效版本回写给实体模型并通知下游。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class ModelChangeService(BaseModuleService):
    MODULE = "model_change"
    ENTITY = "变更单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["变更单号", "实体编码", "变更内容", "审批状态", "生效版本"]
    REQUIRED_FIELDS = ["变更单号", "实体编码", "变更内容"]
    STATUS_ORDER = ["起草中", "待审批", "已生效", "已驳回"]
    ACTION_RULES = {"提交审批": "待审批", "生效变更": "已生效", "驳回变更": "已驳回"}
    NEGATIVE_ACTIONS = ["驳回变更"]

    # ---- 业务扩展：变更审批与版本生效 ----

    def submit_for_approval(self, entry_id: int) -> dict[str, Any]:
        """提交审批：校验实体存在且变更内容完整。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "变更单不存在"}
        entity_code = entry.get("实体编码", "")
        model = next((m for m in store.rows("entity_model")
                      if m.get("实体编码") == entity_code), None)
        if model is None:
            return {"ok": False, "message": f"实体 {entity_code} 不存在"}
        if not str(entry.get("变更内容", "")).strip():
            return {"ok": False, "message": "变更内容为空，不能提交"}
        entry["status"] = "待审批"
        entry["pending"] = True
        return {"ok": True, "entity": entity_code}

    def apply_effective_version(self, entry_id: int) -> dict[str, Any]:
        """生效变更：把生效版本回写实体模型。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "待审批":
            return {"ok": False, "message": "变更单不在待审批状态"}
        entity_code = entry.get("实体编码", "")
        version = str(entry.get("生效版本", "")) or "v1"
        for model in store.rows("entity_model"):
            if model.get("实体编码") == entity_code:
                model["版本号"] = version
                model["status"] = "已发布"
        entry["status"] = "已生效"
        entry["审批状态"] = "已生效"
        entry["生效版本"] = version
        entry["pending"] = False
        return {"ok": True, "version": version}

    def reject_with_reason(self, entry_id: int, reason: str) -> str:
        """驳回变更并记录驳回原因。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return "变更单不存在"
        entry["status"] = "已驳回"
        entry["驳回原因"] = reason
        entry["abnormal"] = True
        return f"变更单 {entry.get('变更单号')} 已驳回: {reason}"

    def consume_entity_versions(self, entry_id: int) -> list[str]:
        """读取实体模型的历史版本序列。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return []
        entity_code = entry.get("实体编码", "")
        return [m.get("版本号", "") for m in store.rows("entity_model")
                if m.get("实体编码") == entity_code]

    def notify_version_change(self, entry_id: int) -> list[str]:
        """版本生效后通知全部订阅方刷新口径。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "已生效":
            return []
        entity_code = entry.get("实体编码", "")
        notified: list[str] = []
        for sub in store.rows("subscriber_mgr"):
            if entity_code in str(sub.get("订阅实体", "")):
                sub["pending"] = True
                notified.append(sub.get("订阅方标识", ""))
        return notified

    def register_change_lineage(self, entry_id: int) -> str | None:
        """登记变更单到实体模型血缘边。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None
        edges = store.rows("lineage_graph")
        edge_id = max((int(r.get("id", 0)) for r in edges), default=0) + 1
        edges.append({
            "id": edge_id,
            "血缘边标识": f"edge-change-{edge_id}",
            "上游节点": entry.get("变更单号", ""),
            "下游节点": entry.get("实体编码", ""),
            "变换规则": "变更生效",
            "登记时间": datetime.now(timezone.utc).isoformat(),
            "status": "已登记",
            "pending": False,
            "abnormal": False,
        })
        return f"edge-change-{edge_id}"
