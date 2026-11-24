"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class IdCrossMapService(BaseModuleService):
    MODULE = "id_cross_map"
    ENTITY = "交叉映射"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["映射批次", "源系统标识", "金记录标识", "映射置信度", "映射状态"]
    REQUIRED_FIELDS = ["映射批次", "源系统标识", "金记录标识"]
    STATUS_ORDER = ["待映射", "已映射", "映射失败"]
    ACTION_RULES = {"执行映射": "已映射", "重试映射": "映射失败"}
    NEGATIVE_ACTIONS = []
