"""重复检测器领域服务：管理主数据疑似重复记录组的检测批次、相似度与置信区间。

数据链路位置：主数据加工层第二环，负责消费清洗产物，
把候选组派发给金记录合并与人工复核。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class DupDetectService(BaseModuleService):
    MODULE = "dup_detect"
    ENTITY = "检测结果"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["检测批次", "实体编码", "候选组数", "相似度算法", "置信区间"]
    REQUIRED_FIELDS = ["检测批次", "实体编码", "候选组数"]
    STATUS_ORDER = ["检测中", "已完成", "检测失败"]
    ACTION_RULES = {"开始检测": "已完成", "重试检测": "检测失败"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：重复检测与合并派发 ----

    def run_detection(self, entry_id: int, similarity: float) -> dict[str, Any]:
        """执行重复检测：按置信区间过滤候选组并更新批次状态。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "检测结果不存在"}
        low, high = 0.85, 1.0
        interval = str(entry.get("置信区间", "[0.85,1.0]"))
        try:
            parts = interval.strip("[]").split(",")
            low, high = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            pass
        if not low <= similarity <= high:
            entry["status"] = "检测失败"
            entry["abnormal"] = True
            return {"ok": False, "message": "相似度不在置信区间内"}
        groups = int(entry.get("候选组数", "0") or 0)
        if similarity >= 0.95:
            groups += 1
            entry["候选组数"] = str(groups)
        entry["status"] = "已完成"
        entry["pending"] = False
        return {"ok": True, "candidate_groups": groups, "similarity": similarity}

    def promote_to_merge(self, entry_id: int) -> dict[str, Any]:
        """把完成检测的候选组提升为金记录合并任务。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "已完成":
            return {"ok": False, "message": "检测批次未完成，不能合并"}
        tasks = store.rows("golden_merge")
        task_id = max((int(r.get("id", 0)) for r in tasks), default=0) + 1
        tasks.append({
            "id": task_id,
            "合并任务": f"merge-{entry.get('检测批次')}-{task_id}",
            "候选组": entry.get("检测批次", ""),
            "实体编码": entry.get("实体编码", ""),
            "生还规则": "置信度最高",
            "合并结果": "",
            "status": "待合并",
            "pending": True,
            "abnormal": False,
        })
        return {"ok": True, "merge_task_id": task_id}

    def send_conflict_review(self, entry_id: int) -> str | None:
        """把疑似冲突候选组送入人工复核队列。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None
        reviews = store.rows("merge_review")
        review_id = max((int(r.get("id", 0)) for r in reviews), default=0) + 1
        reviews.append({
            "id": review_id,
            "记录编号": f"rv-dup-{review_id}",
            "候选组": entry.get("检测批次", ""),
            "复核结论": "疑似重复",
            "复核角色": "数据管理员",
            "复核时间": datetime.now(timezone.utc).isoformat(),
            "status": "待复核",
            "pending": True,
            "abnormal": False,
        })
        return f"rv-dup-{review_id}"

    def consume_cleanse_batches(self, entry_id: int) -> list[Any]:
        """读取清洗模块派发的批次，作为检测输入。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return []
        return [r.get("待清洗批次") for r in store.rows("std_cleanse")
                if r.get("实体编码") == entry.get("实体编码") and r.get("待清洗批次")]

    def snapshot_stats(self, entry_id: int) -> dict[str, Any]:
        """统计检测指标并写入治理看板快照。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {}
        rows = store.rows(self.MODULE)
        dup_rate = sum(int(r.get("候选组数", "0") or 0) for r in rows) / max(len(rows), 1)
        stats = store.rows("stats_overview")
        stat_id = max((int(r.get("id", 0)) for r in stats), default=0) + 1
        stats.append({
            "id": stat_id,
            "统计时间": datetime.now(timezone.utc).isoformat(),
            "实体编码": entry.get("实体编码", ""),
            "金记录数": "0",
            "重复率": f"{dup_rate:.2%}",
            "分发延迟": "0",
            "status": "正常",
            "pending": False,
            "abnormal": False,
        })
        return {"snapshot_id": stat_id, "dup_rate": f"{dup_rate:.2%}"}

    def mark_failed_and_retry(self, entry_id: int, reason: str) -> dict[str, Any]:
        """标记检测失败并登记失败原因，支持断点重试。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "检测结果不存在"}
        entry["status"] = "检测失败"
        entry["abnormal"] = True
        entry["失败原因"] = reason
        return {"ok": False, "message": f"检测失败: {reason}", "retryable": True}
