# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
import pytest
import sqlite3
import tempfile
import os
import gc
from ontology.database import init_ontology_tables
from ontology.init_data import load_sample_ontology_data
from ontology.tools import logical_layer_expansion


class FakeMessage:
    """A fake LLM message for testing."""
    def __init__(self, content: str):
        self.content = content


@pytest.fixture
def db_with_full_sample():
    """Create test database with full sample data"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        load_sample_ontology_data(db_path)
        yield db_path

    finally:
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_integration_city_expansion(db_with_full_sample, monkeypatch):
    """集成测试：城市扩层"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion.invoke({
        "concept_name": "tier1_cities",
        "concept_category": "city"
    })

    assert len(result) == 4
    assert set(result) == {"shanghai", "beijing", "guangzhou", "shenzhen"}


def test_integration_customer_expansion(db_with_full_sample, monkeypatch):
    """集成测试：客户扩层（三级递归）"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion.invoke({
        "concept_name": "bytedance_group",
        "concept_category": "customer"
    })

    assert len(result) == 3
    assert "wuhan_toutiao" in result
    assert "wuhan_douyin" in result
    assert "wuhan_feishu" in result


def test_integration_region_expansion(db_with_full_sample, monkeypatch):
    """集成测试：区域扩层"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion.invoke({
        "concept_name": "east_china",
        "concept_category": "region"
    })

    assert len(result) >= 4  # 至少包含4个城市

    assert len(result) == 4  # shanghai, hangzhou, nanjing, suzhou
    assert set(result) == {"shanghai", "hangzhou", "nanjing", "suzhou"}


def test_end_to_end_workflow(db_with_full_sample, monkeypatch):
    """端到端工作流测试"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    # 1. Expand tier1_cities
    cities = logical_layer_expansion.invoke({
        "concept_name": "tier1_cities",
        "concept_category": "city"
    })
    assert len(cities) > 0

    # 2. Get physical codes
    codes = logical_layer_expansion.invoke({
        "concept_name": "tier1_cities",
        "concept_category": "city",
        "return_type": "physical_code"
    })
    assert len(codes) > 0

    # 3. Get mapping
    mapping = logical_layer_expansion.invoke({
        "concept_name": "tier1_cities",
        "concept_category": "city",
        "return_type": "both"
    })
    assert isinstance(mapping, dict)
    assert len(mapping) > 0


def test_integration_with_aliases(db_with_full_sample, monkeypatch):
    """集成测试：别名支持"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    # 使用中文别名
    result = logical_layer_expansion.invoke({
        "concept_name": "一线城市",
        "concept_category": "city"
    })

    assert len(result) == 4
