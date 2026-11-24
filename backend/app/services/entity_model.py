"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class EntityModelService(BaseModuleService):
    MODULE = "entity_model"
    ENTITY = "实体定义"
    OPERATION_TERM = "合并"
    LIST_FIELDS = ["实体编码", "实体名称", "唯一键规则", "合并策略", "版本号"]
    REQUIRED_FIELDS = ["实体编码", "实体名称", "唯一键规则"]
    STATUS_ORDER = ["草稿", "已发布", "已废弃"]
    ACTION_RULES = {"发布实体": "已发布", "废弃实体": "已废弃"}
    NEGATIVE_ACTIONS = []
