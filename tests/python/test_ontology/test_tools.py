# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
import pytest
import sqlite3
import tempfile
import os
import gc
from unittest.mock import Mock
from ontology.database import init_ontology_tables
from ontology.tools import logical_layer_expansion


class FakeMessage:
    """A fake LLM message for testing."""
    def __init__(self, content: str):
        self.content = content


@pytest.fixture
def db_with_sample_data():
    """Create test database with sample data"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES
                ('tier1_cities', 'abstract_concept', 'city', '一线城市', NULL),
                ('shanghai', 'concrete_instance', 'city', '上海', '{"code": "021"}'),
                ('beijing', 'concrete_instance', 'city', '北京', '{"code": "010"}')
        """)

        concept_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier1_cities'").fetchone()[0]
        for city in ['shanghai', 'beijing']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (concept_id, city_id))

        conn.commit()
        conn.close()
        yield db_path

    finally:
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_logical_layer_expansion_tool(db_with_sample_data, monkeypatch):
    """Test logical layer expansion tool"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_sample_data)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion.invoke({
        "concept_name": "tier1_cities",
        "concept_category": "city",
        "return_type": "business_name"
    })

    assert isinstance(result, list)
    assert len(result) == 2
    assert set(result) == {"shanghai", "beijing"}


def test_logical_layer_expansion_physical_code(db_with_sample_data, monkeypatch):
    """Test returning physical codes"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_sample_data)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion.invoke({
        "concept_name": "tier1_cities",
        "concept_category": "city",
        "return_type": "physical_code"
    })

    assert isinstance(result, list)
    assert all(code in ["021", "010"] for code in result if code)


def test_logical_layer_expansion_both(db_with_sample_data, monkeypatch):
    """Test returning both business name and physical code"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_sample_data)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion.invoke({
        "concept_name": "tier1_cities",
        "concept_category": "city",
        "return_type": "both"
    })

    assert isinstance(result, dict)
    assert "shanghai" in result
    assert result["shanghai"] == "021"
