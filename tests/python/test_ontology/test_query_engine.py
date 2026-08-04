# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
import pytest
import sqlite3
import tempfile
import os
from ontology.database import init_ontology_tables
from ontology.query_engine import OntologyQueryEngine


@pytest.fixture
def db_with_sample_data():
    """创建包含示例数据的测试数据库"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 插入测试数据：一线城市
        cursor.execute("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES
                ('tier1_cities', 'abstract_concept', 'city', '一线城市', NULL),
                ('shanghai', 'concrete_instance', 'city', '上海', '{"code": "021"}'),
                ('beijing', 'concrete_instance', 'city', '北京', '{"code": "010"}'),
                ('guangzhou', 'concrete_instance', 'city', '广州', '{"code": "020"}'),
                ('shenzhen', 'concrete_instance', 'city', '深圳', '{"code": "0755"}')
        """)

        # 建立关系
        concept_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier1_cities'").fetchone()[0]
        for city in ['shanghai', 'beijing', 'guangzhou', 'shenzhen']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (concept_id, city_id))

        conn.commit()
        conn.close()
        yield db_path

    finally:
        os.unlink(db_path)


def test_expand_concept_two_levels(db_with_sample_data):
    """测试两级扩层（城市分类）"""
    engine = OntologyQueryEngine(db_with_sample_data)

    result = engine.expand_concept("tier1_cities", return_type="business_name")

    assert isinstance(result, list)
    assert len(result) == 4
    assert set(result) == {"shanghai", "beijing", "guangzhou", "shenzhen"}


def test_expand_concept_physical_code(db_with_sample_data):
    """测试返回物理编码"""
    engine = OntologyQueryEngine(db_with_sample_data)

    result = engine.expand_concept("tier1_cities", return_type="physical_code")

    assert isinstance(result, list)
    assert len(result) == 4
    # 验证返回的是编码
    assert all(code in ["021", "010", "020", "0755"] for code in result if code)


def test_expand_concept_both(db_with_sample_data):
    """测试返回业务名称和物理编码"""
    engine = OntologyQueryEngine(db_with_sample_data)

    result = engine.expand_concept("tier1_cities", return_type="both")

    assert isinstance(result, dict)
    assert len(result) == 4
    assert "shanghai" in result
    assert result["shanghai"] == "021"


def test_concept_not_found(db_with_sample_data):
    """测试概念未找到"""
    engine = OntologyQueryEngine(db_with_sample_data)

    with pytest.raises(OntologyQueryEngine.ConceptNotFoundError):
        engine.expand_concept("nonexistent_concept")


def test_get_concept_type(db_with_sample_data):
    """测试获取概念类型"""
    engine = OntologyQueryEngine(db_with_sample_data)

    assert engine.get_concept_type("tier1_cities") == "city"
    assert engine.get_concept_type("shanghai") == "city"
