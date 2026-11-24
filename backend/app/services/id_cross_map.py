"""标识交叉映射领域服务：维护源系统标识到金记录标识的映射批次、置信度与失败重试。

数据链路位置：主数据标识层，负责消费合并产物与源系统标识，
把交叉映射结果提供给下游查询与回溯。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class IdCrossMapService(BaseModuleService):
    MODULE = "id_cross_map"
    ENTITY = "交叉映射"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["映射批次", "源系统标识", "金记录标识", "映射置信度", "映射状态"]
    REQUIRED_FIELDS = ["映射批次", "源系统标识", "金记录标识"]
    STATUS_ORDER = ["待映射", "已映射", "映射失败"]
    ACTION_RULES = {"执行映射": "已映射", "重试映射": "映射失败"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：标识映射与合并联动 ----

    def execute_mapping(self, entry_id: int) -> dict[str, Any]:
        """执行交叉映射：校验金记录存在后写映射状态。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "待映射":
            return {"ok": False, "message": "映射批次不在待映射状态"}
        golden_id = str(entry.get("金记录标识", ""))
        merged = [m for m in store.rows("golden_merge")
                  if m.get("status") == "已合并" and golden_id in str(m.get("合并结果", ""))]
        if not merged:
            entry["status"] = "映射失败"
            entry["abnormal"] = True
            return {"ok": False, "message": f"金记录 {golden_id} 未合并完成"}
        entry["status"] = "已映射"
        entry["映射状态"] = "已映射"
        entry["pending"] = False
        return {"ok": True, "golden_id": golden_id}

    def verify_confidence(self, entry_id: int, min_confidence: float) -> dict[str, Any]:
        """校验映射置信度低于阈值时转人工复核。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "交叉映射不存在"}
        raw = str(entry.get("映射置信度", "1.0")).rstrip("%")
        try:
            confidence = float(raw)
        except ValueError:
            confidence = 1.0
        if confidence < min_confidence:
            reviews = store.rows("merge_review")
            review_id = max((int(r.get("id", 0)) for r in reviews), default=0) + 1
            reviews.append({
                "id": review_id,
                "记录编号": f"rv-map-{review_id}",
                "候选组": entry.get("映射批次", ""),
                "复核结论": f"置信度 {confidence} 低于阈值",
                "复核角色": "数据管理员",
                "复核时间": datetime.now(timezone.utc).isoformat(),
                "status": "待复核",
                "pending": True,
                "abnormal": True,
            })
            return {"ok": True, "needs_review": True, "confidence": confidence}
        return {"ok": True, "needs_review": False, "confidence": confidence}

    def lookup_by_source(self, source_id: str) -> list[dict[str, Any]]:
        """按源系统标识反查金记录，供下游回溯。"""
        return [m for m in store.rows(self.MODULE)
                if m.get("源系统标识") == source_id and m.get("status") == "已映射"]

    def consume_merge_golden(self, entry_id: int) -> list[str]:
        """读取合并模块产出的金记录标识集合。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return []
        return [m.get("合并结果", "") for m in store.rows("golden_merge")
                if m.get("status") == "已合并" and m.get("合并结果")]

    def register_lineage_for_map(self, entry_id: int) -> str | None:
        """登记映射批次的血缘边。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None
        edges = store.rows("lineage_graph")
        edge_id = max((int(r.get("id", 0)) for r in edges), default=0) + 1
        edges.append({
            "id": edge_id,
            "血缘边标识": f"edge-map-{edge_id}",
            "上游节点": entry.get("源系统标识", ""),
            "下游节点": entry.get("金记录标识", ""),
            "变换规则": "标识交叉映射",
            "登记时间": datetime.now(timezone.utc).isoformat(),
            "status": "已登记",
            "pending": False,
            "abnormal": False,
        })
        return f"edge-map-{edge_id}"

    def batch_remap(self, source_ids: list[str], golden_id: str) -> int:
        """批量重建一组源标识到同一金记录的映射。"""
        maps = store.rows(self.MODULE)
        mapped = 0
        for src in source_ids:
            map_id = max((int(r.get("id", 0)) for r in maps), default=0) + 1
            maps.append({
                "id": map_id,
                "映射批次": f"remap-{map_id}",
                "源系统标识": src,
                "金记录标识": golden_id,
                "映射置信度": "0.95",
                "映射状态": "已映射",
                "status": "已映射",
                "pending": False,
                "abnormal": False,
            })
            mapped += 1
        return mapped
