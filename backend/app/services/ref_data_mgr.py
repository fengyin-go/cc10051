"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RefDataMgrService(BaseModuleService):
    MODULE = "ref_data_mgr"
    ENTITY = "参考数据集"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["数据集编码", "数据集名称", "码值条目", "生效版本", "映射规则"]
    REQUIRED_FIELDS = ["数据集编码", "数据集名称", "码值条目"]
    STATUS_ORDER = ["草稿", "已发布", "已废弃"]
    ACTION_RULES = {"发布数据集": "已发布", "废弃数据集": "已废弃"}
    NEGATIVE_ACTIONS = []
