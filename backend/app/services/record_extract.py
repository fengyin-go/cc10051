"""记录抽取作业领域服务：管理按游标从源系统抽取主数据记录的作业调度与断点。

数据链路位置：主数据采集层，负责消费源系统登记与同步游标状态，
把抽取产物派发给标准化清洗模块。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class RecordExtractService(BaseModuleService):
    MODULE = "record_extract"
    ENTITY = "抽取作业"
    OPERATION_TERM = "抓取"
    LIST_FIELDS = ["作业名称", "源系统", "实体编码", "抽取范围", "游标位置"]
    REQUIRED_FIELDS = ["作业名称", "源系统", "实体编码"]
    STATUS_ORDER = ["待执行", "执行中", "已完成", "抽取失败"]
    ACTION_RULES = {"启动作业": "执行中", "重试抽取": "抽取失败"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：记录抽取与清洗入链 ----

    def start_with_cursor(self, entry_id: int) -> dict[str, Any]:
        """启动抽取作业，按 sync_cursor 的游标值定位起始位置。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "抽取作业不存在"}
        sys_code = entry.get("源系统", "")
        cursor_row = next((c for c in store.rows("sync_cursor")
                           if c.get("源系统") == sys_code and c.get("status") == "正常"), None)
        cursor_value = str(cursor_row.get("游标值", "0")) if cursor_row else "0"
        entry["游标位置"] = cursor_value
        entry["status"] = "执行中"
        entry["pending"] = True
        return {"ok": True, "cursor": cursor_value}

    def complete_and_advance(self, entry_id: int, record_count: int) -> dict[str, Any]:
        """完成抽取并推进游标，向 std_cleanse 派发清洗任务。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "执行中":
            return {"ok": False, "message": "作业不在执行中状态"}
        entry["status"] = "已完成"
        entry["pending"] = False
        new_cursor = str(int(entry.get("游标位置", "0") or 0) + record_count)
        entry["游标位置"] = new_cursor
        for cur in store.rows("sync_cursor"):
            if cur.get("源系统") == entry.get("源系统"):
                cur["游标值"] = new_cursor
                cur["推进时间"] = datetime.now(timezone.utc).isoformat()
        return {"ok": True, "records": record_count, "cursor": new_cursor}

    def fail_with_retry(self, entry_id: int, reason: str) -> dict[str, Any]:
        """标记抽取失败并写回游标回退标记。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "抽取作业不存在"}
        entry["status"] = "抽取失败"
        entry["abnormal"] = True
        for cur in store.rows("sync_cursor"):
            if cur.get("源系统") == entry.get("源系统"):
                cur["回退标记"] = "是"
                cur["status"] = "已回退"
        return {"ok": False, "message": f"抽取失败: {reason}", "retry_hint": "可执行重试抽取"}

    def dispatch_cleanse(self, entry_id: int) -> int:
        """把抽取结果派发给标准化清洗模块。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "已完成":
            return 0
        rules = store.rows("std_cleanse")
        enabled = [r for r in rules if r.get("status") == "已启用"
                   and r.get("实体编码") == entry.get("实体编码")]
        dispatched = 0
        for rule in enabled:
            rule.setdefault("待清洗批次", []).append(entry.get("作业名称", ""))
            dispatched += 1
        return dispatched

    def consume_source_config(self, entry_id: int) -> dict[str, Any] | None:
        """读取源系统登记信息，确认抽取目标可用。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None
        sys_code = entry.get("源系统", "")
        return next((s for s in store.rows("source_system")
                     if s.get("系统标识") == sys_code and s.get("status") == "已接入"), None)

    def batch_extract(self, sys_code: str, entity_code: str, ranges: list[str]) -> list[int]:
        """批量创建抽取作业，一次提交整组作业。"""
        jobs = store.rows(self.MODULE)
        created: list[int] = []
        for rng in ranges:
            job_id = max((int(r.get("id", 0)) for r in jobs), default=0) + 1
            jobs.append({
                "id": job_id,
                "作业名称": f"batch-{entity_code}-{job_id}",
                "源系统": sys_code,
                "实体编码": entity_code,
                "抽取范围": rng,
                "游标位置": "0",
                "status": "待执行",
                "pending": True,
                "abnormal": False,
            })
            created.append(job_id)
        return created
