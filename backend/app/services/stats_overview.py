"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class StatsOverviewService(BaseModuleService):
    MODULE = "stats_overview"
    ENTITY = "统计快照"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["统计时间", "实体编码", "金记录数", "重复率", "分发延迟"]
    REQUIRED_FIELDS = ["统计时间", "实体编码", "金记录数"]
    STATUS_ORDER = ["正常", "指标越界", "数据缺失"]
    ACTION_RULES = {"重算快照": "指标越界", "忽略告警": "数据缺失"}
    NEGATIVE_ACTIONS = ["忽略告警"]
