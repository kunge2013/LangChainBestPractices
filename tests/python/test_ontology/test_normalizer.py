# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
# tests/python/test_ontology/test_normalizer.py
import pytest
from ontology.normalizer import ConceptNameNormalizer

def test_normalize_direct_match():
    """测试直接匹配"""
    assert ConceptNameNormalizer.normalize("tier1_cities") == "tier1_cities"
    assert ConceptNameNormalizer.normalize("bytedance_group") == "bytedance_group"


def test_normalize_alias_mapping():
    """测试别名映射"""
    assert ConceptNameNormalizer.normalize("一线城市") == "tier1_cities"
    assert ConceptNameNormalizer.normalize("ByteDance") == "bytedance_group"
    assert ConceptNameNormalizer.normalize("头条系") == "bytedance_group"


def test_normalize_case_insensitive():
    """测试大小写不敏感"""
    assert ConceptNameNormalizer.normalize("TIER1_CITIES") == "tier1_cities"
    assert ConceptNameNormalizer.normalize("BYTEDANCE") == "bytedance_group"


def test_normalize_no_alias():
    """测试无别名返回原值"""
    result = ConceptNameNormalizer.normalize("unknown_concept")
    assert result == "unknown_concept"


def test_add_alias():
    """测试动态添加别名"""
    ConceptNameNormalizer.add_alias("二线城市", "tier2_cities")
    assert ConceptNameNormalizer.normalize("二线城市") == "tier2_cities"
