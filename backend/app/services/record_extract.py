"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RecordExtractService(BaseModuleService):
    MODULE = "record_extract"
    ENTITY = "抽取作业"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["作业名称", "源系统", "实体编码", "抽取范围", "游标位置"]
    REQUIRED_FIELDS = ["作业名称", "源系统", "实体编码"]
    STATUS_ORDER = ["待执行", "执行中", "已完成", "抽取失败"]
    ACTION_RULES = {"启动作业": "执行中", "重试抽取": "抽取失败"}
    NEGATIVE_ACTIONS = []
