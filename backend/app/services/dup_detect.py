"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DupDetectService(BaseModuleService):
    MODULE = "dup_detect"
    ENTITY = "检测结果"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["检测批次", "实体编码", "候选组数", "相似度算法", "置信区间"]
    REQUIRED_FIELDS = ["检测批次", "实体编码", "候选组数"]
    STATUS_ORDER = ["检测中", "已完成", "检测失败"]
    ACTION_RULES = {"开始检测": "已完成", "重试检测": "检测失败"}
    NEGATIVE_ACTIONS = []
