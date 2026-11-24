"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class QualityResultService(BaseModuleService):
    MODULE = "quality_result"
    ENTITY = "质量结果"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["报告批次", "实体编码", "检查总数", "命中数", "评分结果"]
    REQUIRED_FIELDS = ["报告批次", "实体编码", "检查总数"]
    STATUS_ORDER = ["生成中", "已生成", "生成失败"]
    ACTION_RULES = {"生成报告": "已生成", "重试生成": "生成失败"}
    NEGATIVE_ACTIONS = []
