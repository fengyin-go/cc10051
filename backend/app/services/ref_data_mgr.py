"""参考数据管理领域服务：管理参考数据集的码值条目、生效版本与码值映射规则。

数据链路位置：主数据标准化支撑层，负责消费清洗与校验环节的码表需求，
把参考码值派发给标准化清洗和质量规则使用。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class RefDataMgrService(BaseModuleService):
    MODULE = "ref_data_mgr"
    ENTITY = "参考数据集"
    OPERATION_TERM = "标准化"
    LIST_FIELDS = ["数据集编码", "数据集名称", "码值条目", "生效版本", "映射规则"]
    REQUIRED_FIELDS = ["数据集编码", "数据集名称", "码值条目"]
    STATUS_ORDER = ["草稿", "已发布", "已废弃"]
    ACTION_RULES = {"发布数据集": "已发布", "废弃数据集": "已废弃"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：码值发布与标准化联动 ----

    def publish_dataset(self, entry_id: int) -> dict[str, Any]:
        """发布参考数据集并递增生效版本。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "草稿":
            return {"ok": False, "message": "数据集不在草稿状态"}
        old_ver = str(entry.get("生效版本", "v1"))
        try:
            new_ver = f"v{int(old_ver.lstrip('v') or 1) + 1}"
        except ValueError:
            new_ver = old_ver
        entry["生效版本"] = new_ver
        entry["status"] = "已发布"
        entry["pending"] = False
        return {"ok": True, "version": new_ver, "dataset": entry.get("数据集编码")}

    def normalize_code(self, entry_id: int, raw_value: str) -> dict[str, Any]:
        """按映射规则把原始码值标准化为标准码。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "已发布":
            return {"ok": False, "message": "参考数据集未发布"}
        items = str(entry.get("码值条目", ""))
        pairs = [pair.split("=") for pair in items.split(",") if "=" in pair]
        mapping = {src.strip(): dst.strip() for src, dst in pairs}
        normalized = mapping.get(raw_value.strip(), raw_value.strip().upper())
        return {"ok": True, "raw": raw_value, "normalized": normalized,
                "mapped": raw_value.strip() in mapping}

    def bind_to_cleanse(self, entry_id: int) -> int:
        """把参考数据集绑定给清洗规则做码值标准化。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return 0
        bound = 0
        for rule in store.rows("std_cleanse"):
            if rule.get("status") == "已启用" and not rule.get("参考码表"):
                rule["参考码表"] = entry.get("数据集编码", "")
                bound += 1
        return bound

    def consume_quality_dimensions(self, entry_id: int) -> list[str]:
        """读取质量规则的检查维度，对齐码值口径。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return []
        return [q.get("检查维度", "") for q in store.rows("quality_rule")
                if q.get("status") == "已启用" and q.get("检查维度")]

    def deprecate_dataset(self, entry_id: int, reason: str) -> str:
        """废弃数据集并解绑清洗规则引用。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return "参考数据集不存在"
        entry["status"] = "已废弃"
        entry["废弃原因"] = reason
        code = entry.get("数据集编码", "")
        unbound = 0
        for rule in store.rows("std_cleanse"):
            if rule.get("参考码表") == code:
                rule["参考码表"] = ""
                unbound += 1
        return f"数据集 {code} 已废弃，解绑 {unbound} 条清洗规则"

    def list_versions(self, entity_code: str) -> list[str]:
        """列出某数据集的历史生效版本序列。"""
        return [r.get("生效版本", "") for r in store.rows(self.MODULE)
                if entity_code in str(r.get("数据集编码", "")) and r.get("生效版本")]
