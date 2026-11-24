"""合并复核队列领域服务：管理人工裁决合并冲突候选组的复核记录、结论回写与批量办结。

数据链路位置：人工治理环节，负责消费合并冲突任务，
把裁决结论回写给合并任务并派发重新检测。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class MergeReviewService(BaseModuleService):
    MODULE = "merge_review"
    ENTITY = "复核记录"
    OPERATION_TERM = "合并"
    LIST_FIELDS = ["记录编号", "候选组", "复核结论", "复核角色", "复核时间"]
    REQUIRED_FIELDS = ["记录编号", "候选组", "复核结论"]
    STATUS_ORDER = ["待复核", "已通过", "已驳回"]
    ACTION_RULES = {"通过记录": "已通过", "驳回记录": "已驳回"}
    NEGATIVE_ACTIONS = ["驳回记录"]

    # ---- 业务扩展：人工复核与合并回写 ----

    def approve_record(self, entry_id: int, reviewer: str) -> dict[str, Any]:
        """通过复核并把结论回写合并任务。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "待复核":
            return {"ok": False, "message": "记录不在待复核状态"}
        entry["status"] = "已通过"
        entry["复核结论"] = "确认合并"
        entry["复核角色"] = reviewer
        entry["复核时间"] = datetime.now(timezone.utc).isoformat()
        entry["pending"] = False
        group = entry.get("候选组", "")
        for task in store.rows("golden_merge"):
            if task.get("候选组") == group and task.get("status") == "合并冲突":
                task["status"] = "已合并"
                task["合并结果"] = f"GR-{group}-R"
                task["pending"] = False
        return {"ok": True, "group": group, "reviewer": reviewer}

    def reject_record(self, entry_id: int, reviewer: str, reason: str) -> dict[str, Any]:
        """驳回复核并退回重复检测重排。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "待复核":
            return {"ok": False, "message": "记录不在待复核状态"}
        entry["status"] = "已驳回"
        entry["复核结论"] = f"驳回: {reason}"
        entry["复核角色"] = reviewer
        entry["复核时间"] = datetime.now(timezone.utc).isoformat()
        entry["abnormal"] = True
        group = entry.get("候选组", "")
        batches = store.rows("dup_detect")
        batch_id = max((int(r.get("id", 0)) for r in batches), default=0) + 1
        batches.append({
            "id": batch_id,
            "检测批次": f"redetect-{group}-{batch_id}",
            "实体编码": "",
            "候选组数": "0",
            "相似度算法": "编辑距离",
            "置信区间": "[0.90,1.0]",
            "status": "检测中",
            "pending": True,
            "abnormal": False,
        })
        return {"ok": True, "redetect_batch": batch_id}

    def consume_conflicts(self, entry_id: int) -> list[dict[str, Any]]:
        """读取合并冲突任务，生成本复核队列输入。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return []
        group = entry.get("候选组", "")
        return [t for t in store.rows("golden_merge")
                if t.get("候选组") == group and t.get("status") == "合并冲突"]

    def bulk_approve(self, reviewer: str, max_count: int) -> int:
        """批量通过待复核记录，一次提交整组。"""
        approved = 0
        for row in store.rows(self.MODULE):
            if approved >= max_count:
                break
            if row.get("status") == "待复核":
                row["status"] = "已通过"
                row["复核角色"] = reviewer
                row["复核时间"] = datetime.now(timezone.utc).isoformat()
                row["pending"] = False
                approved += 1
        return approved

    def stats_pending_by_role(self) -> dict[str, int]:
        """按复核角色统计待复核量，供容量排班。"""
        counter: dict[str, int] = {}
        for row in store.rows(self.MODULE):
            if row.get("status") == "待复核":
                role = row.get("复核角色", "未指派")
                counter[role] = counter.get(role, 0) + 1
        return counter

    def archive_reviewed(self, days: int) -> int:
        """归档已办结的复核记录。"""
        archived = 0
        for row in store.rows(self.MODULE):
            if row.get("status") in ("已通过", "已驳回"):
                row["归档"] = True
                row["归档天数"] = days
                archived += 1
        return archived
