"""源系统登记领域服务：管理主数据来源系统的登记、接入激活、停用与责任边界维护。

数据链路位置：主数据治理链路源头，负责登记源系统并把接入信号传递给
抽取作业与同步游标，是抽取链路的第一个上游。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class SourceSystemService(BaseModuleService):
    MODULE = "source_system"
    ENTITY = "源系统"
    OPERATION_TERM = "接入"
    LIST_FIELDS = ["系统标识", "系统名称", "数据域", "同步频率", "责任人"]
    REQUIRED_FIELDS = ["系统标识", "系统名称", "数据域"]
    STATUS_ORDER = ["待接入", "已接入", "已停用"]
    ACTION_RULES = {"接入系统": "已接入", "停用系统": "已停用"}
    NEGATIVE_ACTIONS = ["停用系统"]

    # ---- 业务扩展：源系统接入与抽取联动 ----

    def register_and_activate(self, system_id: str, name: str, domain: str, owner: str) -> dict[str, Any]:
        """登记并激活源系统，写入源系统数据集。"""
        rows = store.rows(self.MODULE)
        if any(r.get("系统标识") == system_id for r in rows):
            return {"ok": False, "message": f"源系统 {system_id} 已登记"}
        entry = {"id": max((int(r.get("id", 0)) for r in rows), default=0) + 1}
        entry.update({"系统标识": system_id, "系统名称": name, "数据域": domain,
                      "同步频率": "每日", "责任人": owner, "status": "已接入",
                      "pending": False, "abnormal": False})
        rows.append(entry)
        return {"ok": True, "entry_id": entry["id"], "message": f"源系统 {system_id} 已接入"}

    def push_extract_job(self, entry_id: int) -> dict[str, Any]:
        """为已接入的源系统创建抽取作业，形成接入→抽取链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "已接入":
            return {"ok": False, "message": "源系统不存在或未接入"}
        jobs = store.rows("record_extract")
        job_id = max((int(r.get("id", 0)) for r in jobs), default=0) + 1
        jobs.append({
            "id": job_id,
            "作业名称": f"抽取-{entry.get('系统标识')}-{job_id}",
            "源系统": entry.get("系统标识", ""),
            "实体编码": "",
            "抽取范围": "全量",
            "游标位置": "0",
            "status": "待执行",
            "pending": True,
            "abnormal": False,
        })
        return {"ok": True, "job_id": job_id}

    def ensure_cursor(self, entry_id: int) -> dict[str, Any]:
        """为源系统初始化同步游标，写入 sync_cursor 模块。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "源系统不存在"}
        cursors = store.rows("sync_cursor")
        cursor_id = max((int(r.get("id", 0)) for r in cursors), default=0) + 1
        cursors.append({
            "id": cursor_id,
            "源系统": entry.get("系统标识", ""),
            "实体编码": "",
            "游标值": "0",
            "推进时间": datetime.now(timezone.utc).isoformat(),
            "回退标记": "否",
            "status": "正常",
            "pending": False,
            "abnormal": False,
        })
        return {"ok": True, "cursor_id": cursor_id}

    def stop_and_disconnect(self, entry_id: int, reason: str) -> str:
        """停用源系统并把关联游标记为停滞。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return "源系统不存在"
        entry["status"] = "已停用"
        entry["abnormal"] = True
        for cur in store.rows("sync_cursor"):
            if cur.get("源系统") == entry.get("系统标识"):
                cur["status"] = "游标停滞"
                cur["pending"] = True
        return f"源系统已停用，原因: {reason}"

    def list_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """按数据域筛选源系统，供血缘登记使用。"""
        return [r for r in store.rows(self.MODULE) if domain in str(r.get("数据域", ""))]

    def register_lineage_edge(self, entry_id: int, downstream: str) -> str | None:
        """登记源系统到下游节点的血缘边。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None
        edges = store.rows("lineage_graph")
        edge_id = max((int(r.get("id", 0)) for r in edges), default=0) + 1
        edges.append({
            "id": edge_id,
            "血缘边标识": f"edge-{entry_id}-{edge_id}",
            "上游节点": entry.get("系统标识", ""),
            "下游节点": downstream,
            "变换规则": "直接同步",
            "登记时间": datetime.now(timezone.utc).isoformat(),
            "status": "已登记",
            "pending": False,
            "abnormal": False,
        })
        return f"edge-{entry_id}-{edge_id}"
