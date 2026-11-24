"""治理看板数据领域服务：管理主数据治理核心指标的时序快照、越界判定与重算。

数据链路位置：治理指标层汇总端，负责消费发布/检测/分发各环节数据，
把重复率与分发延迟快照输出给看板展示。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class StatsOverviewService(BaseModuleService):
    MODULE = "stats_overview"
    ENTITY = "统计快照"
    OPERATION_TERM = "计算"
    LIST_FIELDS = ["统计时间", "实体编码", "金记录数", "重复率", "分发延迟"]
    REQUIRED_FIELDS = ["统计时间", "实体编码", "金记录数"]
    STATUS_ORDER = ["正常", "指标越界", "数据缺失"]
    ACTION_RULES = {"重算快照": "指标越界", "忽略告警": "数据缺失"}
    NEGATIVE_ACTIONS = ["忽略告警"]

    # ---- 业务扩展：指标汇总与越界判定 ----

    def recompute_snapshot(self, entry_id: int) -> dict[str, Any]:
        """重算快照：从发布与检测模块聚合最新指标。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "统计快照不存在"}
        golden_rows = [p for p in store.rows("golden_publish") if p.get("status") == "已发布"]

        def _to_int(raw: Any) -> int:
            try:
                return int(str(raw or "0").strip())
            except ValueError:
                return 0

        golden_count = sum(_to_int(p.get("金记录数")) for p in golden_rows)
        dup_rows = store.rows("dup_detect")
        dup_rate = (sum(_to_int(d.get("候选组数")) for d in dup_rows)
                    / max(len(dup_rows), 1))
        entry["金记录数"] = str(golden_count)
        entry["重复率"] = f"{dup_rate:.2%}"
        entry["统计时间"] = datetime.now(timezone.utc).isoformat()
        entry["status"] = "正常"
        return {"ok": True, "golden_count": golden_count, "dup_rate": f"{dup_rate:.2%}"}

    def check_thresholds(self, entry_id: int, max_dup_rate: float) -> dict[str, Any]:
        """按阈值口径判定指标越界并升级状态。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "统计快照不存在"}
        raw = str(entry.get("重复率", "0%")).rstrip("%")
        try:
            dup_rate = float(raw) / 100 if float(raw) > 1 else float(raw)
        except ValueError:
            dup_rate = 0.0
        if dup_rate > max_dup_rate:
            entry["status"] = "指标越界"
            entry["pending"] = True
            entry["abnormal"] = True
            return {"ok": True, "breach": True, "dup_rate": dup_rate, "threshold": max_dup_rate}
        entry["status"] = "正常"
        return {"ok": True, "breach": False, "dup_rate": dup_rate, "threshold": max_dup_rate}

    def consume_publish_stats(self, entry_id: int) -> dict[str, Any]:
        """读取发布模块的金记录产量。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {}
        rows = [p for p in store.rows("golden_publish") if p.get("status") == "已发布"]
        return {"published": len(rows),
                "golden_total": sum(int(p.get("金记录数", "0") or 0) for p in rows)}

    def consume_dist_latency(self, entry_id: int) -> dict[str, Any]:
        """读取分发模块的积压量估算分发延迟。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {}
        rows = store.rows("dist_task")
        backlog = sum(1 for t in rows if t.get("status") in ("排队中", "分发中"))
        failed = sum(1 for t in rows if t.get("status") == "分发失败")
        latency = backlog * 10 + failed * 30
        entry["分发延迟"] = str(latency)
        return {"backlog": backlog, "failed": failed, "latency_minutes": latency}

    def ignore_alert(self, entry_id: int, reason: str) -> str:
        """忽略越界告警并记录忽略原因。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return "统计快照不存在"
        entry["status"] = "数据缺失"
        entry["忽略原因"] = reason
        entry["pending"] = False
        return f"告警已忽略: {reason}"

    def export_trend_series(self, entity_code: str) -> list[dict[str, Any]]:
        """导出某实体的指标时序序列，供看板绘制。"""
        return [{"统计时间": r.get("统计时间", ""), "金记录数": r.get("金记录数", "0"),
                 "重复率": r.get("重复率", "0%")}
                for r in store.rows(self.MODULE)
                if r.get("实体编码") == entity_code]
