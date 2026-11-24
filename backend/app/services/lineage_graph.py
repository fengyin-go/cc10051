"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class LineageGraphService(BaseModuleService):
    MODULE = "lineage_graph"
    ENTITY = "血缘边"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["血缘边标识", "上游节点", "下游节点", "变换规则", "登记时间"]
    REQUIRED_FIELDS = ["血缘边标识", "上游节点", "下游节点"]
    STATUS_ORDER = ["已登记", "待核验", "失效"]
    ACTION_RULES = {"登记血缘": "已登记", "核验血缘": "待核验"}
    NEGATIVE_ACTIONS = []
