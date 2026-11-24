"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SyncCursorService(BaseModuleService):
    MODULE = "sync_cursor"
    ENTITY = "游标记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["源系统", "实体编码", "游标值", "推进时间", "回退标记"]
    REQUIRED_FIELDS = ["源系统", "实体编码", "游标值"]
    STATUS_ORDER = ["正常", "游标停滞", "已回退"]
    ACTION_RULES = {"推进游标": "游标停滞", "回退游标": "已回退"}
    NEGATIVE_ACTIONS = []
