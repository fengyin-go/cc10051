"""金记录发布领域服务：管理金记录版本的发布批次、版本标识、扇出分发与回滚衔接，完成入库动作。

数据链路位置：主数据发布层，负责消费合并产物，把发布版本
扇出给订阅方并衔接版本回滚任务。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class GoldenPublishService(BaseModuleService):
    MODULE = "golden_publish"
    ENTITY = "发布批次"
    OPERATION_TERM = "入库"
    LIST_FIELDS = ["发布批次", "实体编码", "金记录数", "发布时间", "版本标识"]
    REQUIRED_FIELDS = ["发布批次", "实体编码", "金记录数"]
    STATUS_ORDER = ["待发布", "已发布", "已回滚"]
    ACTION_RULES = {"发布批次": "已发布", "回滚批次": "已回滚"}
    NEGATIVE_ACTIONS = ["回滚批次"]

    # ---- 业务扩展：金记录发布与分发衔接 ----

    def release_version(self, entry_id: int) -> dict[str, Any]:
        """发布金记录版本，写发布时间与版本标识。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "待发布":
            return {"ok": False, "message": "发布批次不在待发布状态"}
        now = datetime.now(timezone.utc).isoformat()
        version = f"pub-v{entry_id}-{now[:10]}"
        entry["发布时间"] = now
        entry["版本标识"] = version
        entry["status"] = "已发布"
        entry["pending"] = False
        return {"ok": True, "version": version, "released_at": now}

    def fanout_to_subscribers(self, entry_id: int) -> list[int]:
        """把已发布版本扇出给全部生效订阅方，生成分发批次。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "已发布":
            return []
        tasks = store.rows("dist_task")
        created: list[int] = []
        for sub in store.rows("subscriber_mgr"):
            if sub.get("status") != "已生效":
                continue
            task_id = max((int(r.get("id", 0)) for r in tasks), default=0) + 1
            tasks.append({
                "id": task_id,
                "分发批次": f"dist-{entry_id}-{task_id}",
                "订阅方": sub.get("订阅方标识", ""),
                "记录范围": f"版本 {entry.get('版本标识', '')}",
                "分发状态": "排队中",
                "回执状态": "未回收",
                "status": "排队中",
                "pending": True,
                "abnormal": False,
            })
            created.append(task_id)
        return created

    def rollback_version(self, entry_id: int, reason: str) -> dict[str, Any]:
        """回滚发布版本并触发版本回滚任务。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "已发布":
            return {"ok": False, "message": "批次未发布，无法回滚"}
        entry["status"] = "已回滚"
        entry["abnormal"] = True
        rollbacks = store.rows("version_rollback")
        rb_id = max((int(r.get("id", 0)) for r in rollbacks), default=0) + 1
        rollbacks.append({
            "id": rb_id,
            "回滚任务": f"rb-{entry_id}-{rb_id}",
            "目标版本": entry.get("版本标识", ""),
            "回滚原因": reason,
            "执行状态": "待执行",
            "影响订阅方": "",
            "status": "待执行",
            "pending": True,
            "abnormal": True,
        })
        return {"ok": True, "rollback_id": rb_id, "message": "回滚任务已创建"}

    def consume_merge_output(self, entry_id: int) -> list[dict[str, Any]]:
        """读取合并模块产出的金记录，作为发布输入。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return []
        return [m for m in store.rows("golden_merge")
                if m.get("实体编码") == entry.get("实体编码") and m.get("status") == "已合并"]

    def emit_stats_snapshot(self, entry_id: int) -> int:
        """发布完成后向治理看板输黄金记录数快照。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return 0
        stats = store.rows("stats_overview")
        stat_id = max((int(r.get("id", 0)) for r in stats), default=0) + 1
        stats.append({
            "id": stat_id,
            "统计时间": datetime.now(timezone.utc).isoformat(),
            "实体编码": entry.get("实体编码", ""),
            "金记录数": str(entry.get("金记录数", "0")),
            "重复率": "0%",
            "分发延迟": "0",
            "status": "正常",
            "pending": False,
            "abnormal": False,
        })
        return stat_id

    def register_publish_lineage(self, entry_id: int) -> str | None:
        """登记发布批次到分发模块的血缘边。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None
        edges = store.rows("lineage_graph")
        edge_id = max((int(r.get("id", 0)) for r in edges), default=0) + 1
        edges.append({
            "id": edge_id,
            "血缘边标识": f"edge-pub-{edge_id}",
            "上游节点": entry.get("发布批次", ""),
            "下游节点": "dist_task",
            "变换规则": "版本分发",
            "登记时间": datetime.now(timezone.utc).isoformat(),
            "status": "已登记",
            "pending": False,
            "abnormal": False,
        })
        return f"edge-pub-{edge_id}"
