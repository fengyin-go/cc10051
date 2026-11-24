"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ModelChangeService(BaseModuleService):
    MODULE = "model_change"
    ENTITY = "变更单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["变更单号", "实体编码", "变更内容", "审批状态", "生效版本"]
    REQUIRED_FIELDS = ["变更单号", "实体编码", "变更内容"]
    STATUS_ORDER = ["起草中", "待审批", "已生效", "已驳回"]
    ACTION_RULES = {"提交审批": "待审批", "生效变更": "已生效", "驳回变更": "已驳回"}
    NEGATIVE_ACTIONS = ["驳回变更"]
