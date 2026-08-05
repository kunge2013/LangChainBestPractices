# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
概念名称标准化器
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ConceptNameNormalizer:
    """
    概念名称标准化器

    处理概念名称的别名映射、大小写转换、模糊匹配等
    """

    # [AGC:START] tool=Cc author=fangkun
    # 预定义的别名映射表
    ALIAS_MAP: Dict[str, str] = {
        # 城市分类
        "一线城市": "tier1_cities",
        "tier1_cities": "tier1_cities",
        "tier 1 cities": "tier1_cities",
        "tier1": "tier1_cities",

        # 客户分类
        "字节跳动": "bytedance_group",
        "bytedance": "bytedance_group",
        "bytedance_group": "bytedance_group",
        "头条系": "bytedance_group",
        "字节跳动集团": "bytedance_group",

        # 区域分类
        "华东区": "east_china",
        "east_china": "east_china",
        "华东地区": "east_china",
        "east china": "east_china",
    }
    # [AGC:END]

    @classmethod
    def normalize(cls, concept_name: str) -> str:
        """
        标准化概念名称

        参数:
            concept_name: 原始概念名称

        返回:
            标准化的概念名称（小写）
        """
        if not concept_name:
            return concept_name

        # [AGC:START] tool=Cc author=fangkun
        # 转换为小写用于匹配
        concept_lower = concept_name.strip().lower()

        # 先尝试直接匹配（小写）
        if concept_lower in cls.ALIAS_MAP:
            return cls.ALIAS_MAP[concept_lower]

        # 最小长度保护：短字符串的模糊匹配容易产生误判
        if len(concept_lower) >= 4:
            # 遍历别名映射，尝试模糊匹配
            for alias, canonical in cls.ALIAS_MAP.items():
                alias_lower = alias.lower()
                # 检查是否包含别名或别名包含它
                if concept_lower in alias_lower or alias_lower in concept_lower:
                    return canonical

        # 没有匹配，返回原始名称的小写形式
        return concept_lower
        # [AGC:END]

    @classmethod
    def add_alias(cls, alias: str, canonical_name: str) -> None:
        """
        动态添加别名映射

        参数:
            alias: 别名
            canonical_name: 标准名称
        """
        # [AGC:START] tool=Cc author=fangkun
        cls.ALIAS_MAP[alias.lower()] = canonical_name.lower()
        logger.info(f"添加别名映射: {alias} -> {canonical_name}")
        # [AGC:END]
