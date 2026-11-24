"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SourceSystemService(BaseModuleService):
    MODULE = "source_system"
    ENTITY = "源系统"
    OPERATION_TERM = "接入"
    LIST_FIELDS = ["系统标识", "系统名称", "数据域", "同步频率", "责任人"]
    REQUIRED_FIELDS = ["系统标识", "系统名称", "数据域"]
    STATUS_ORDER = ["待接入", "已接入", "已停用"]
    ACTION_RULES = {"接入系统": "已接入", "停用系统": "已停用"}
    NEGATIVE_ACTIONS = ["停用系统"]
