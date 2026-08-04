# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
import pytest
import sqlite3
import json
import tempfile
import os
import gc
from unittest.mock import Mock
from ontology.database import init_ontology_tables
from ontology.query_engine import OntologyQueryEngine
from ontology.expander import OntologyExpander


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


def test_expand_database_hit(db_with_sample_data):
    """Test database hit"""
    mock_llm = Mock()
    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=mock_llm,
        enable_llm_reasoning=False
    )

    result = expander.expand("tier1_cities")

    assert isinstance(result, list)
    assert len(result) == 2
    assert set(result) == {"shanghai", "beijing"}

    # Verify LLM was NOT called
    mock_llm.invoke.assert_not_called()


def test_expand_llm_fallback(db_with_sample_data):
    """Test LLM fallback"""
    mock_llm = Mock()
    response_data = {"instances": [{"name": "杭州"}, {"name": "南京"}], "confidence": 0.9}
    mock_llm.invoke.return_value = FakeMessage(json.dumps(response_data, ensure_ascii=False))

    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=mock_llm,
        enable_llm_reasoning=True
    )

    result = expander.expand("tier2_cities")

    assert isinstance(result, list)
    assert "杭州" in result
    assert "南京" in result

    # Verify LLM was called
    mock_llm.invoke.assert_called_once()


def test_expand_with_normalization(db_with_sample_data):
    """Test concept name normalization"""
    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=Mock(),
        enable_llm_reasoning=False
    )

    result = expander.expand("一线城市")

    assert set(result) == {"shanghai", "beijing"}


def test_expand_learning_mode(db_with_sample_data):
    """Test learning mode"""
    mock_llm = Mock()
    response_data = {"instances": [{"name": "深圳"}, {"name": "广州"}], "confidence": 0.95}
    mock_llm.invoke.return_value = FakeMessage(json.dumps(response_data, ensure_ascii=False))

    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=mock_llm,
        enable_llm_reasoning=True,
        enable_learning_mode=True
    )

    # Use a concept name that won't match existing aliases
    result = expander.expand("completely_new_cities")

    assert isinstance(result, list)

    # Verify data was written to database
    conn = sqlite3.connect(db_with_sample_data)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ontology_nodes WHERE node_name = 'completely_new_cities'")
    assert cursor.fetchone()[0] == 1
    conn.close()


def test_expand_both_disabled(db_with_sample_data):
    """Test when both database and LLM are disabled"""
    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=None,
        enable_llm_reasoning=False
    )

    result = expander.expand("nonexistent_concept")

    assert result == []
