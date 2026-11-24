"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class VersionRollbackService(BaseModuleService):
    MODULE = "version_rollback"
    ENTITY = "回滚任务"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["回滚任务", "目标版本", "回滚原因", "执行状态", "影响订阅方"]
    REQUIRED_FIELDS = ["回滚任务", "目标版本", "回滚原因"]
    STATUS_ORDER = ["待执行", "已回滚", "回滚失败"]
    ACTION_RULES = {"执行回滚": "已回滚", "取消任务": "回滚失败"}
    NEGATIVE_ACTIONS = []
