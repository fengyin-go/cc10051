"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SubscriberMgrService(BaseModuleService):
    MODULE = "subscriber_mgr"
    ENTITY = "订阅方"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["订阅方标识", "订阅实体", "分发格式", "订阅过滤", "生效状态"]
    REQUIRED_FIELDS = ["订阅方标识", "订阅实体", "分发格式"]
    STATUS_ORDER = ["待生效", "已生效", "已暂停"]
    ACTION_RULES = {"生效订阅": "已生效", "暂停订阅": "已暂停"}
    NEGATIVE_ACTIONS = []
