"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class GoldenMergeService(BaseModuleService):
    MODULE = "golden_merge"
    ENTITY = "合并任务"
    OPERATION_TERM = "合并"
    LIST_FIELDS = ["合并任务", "实体编码", "候选组", "生还规则", "合并结果"]
    REQUIRED_FIELDS = ["合并任务", "实体编码", "候选组"]
    STATUS_ORDER = ["待合并", "已合并", "合并冲突"]
    ACTION_RULES = {"执行合并": "已合并", "转人工": "合并冲突"}
    NEGATIVE_ACTIONS = []
