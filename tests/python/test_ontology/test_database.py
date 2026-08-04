# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
import pytest
import sqlite3
import tempfile
import os
from ontology.database import init_ontology_tables, drop_ontology_tables

def test_init_ontology_tables():
    """测试本体表初始化"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 验证ontology_nodes表存在且有正确字段
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ontology_nodes'")
        assert cursor.fetchone() is not None

        cursor.execute("PRAGMA table_info(ontology_nodes)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = ['id', 'node_name', 'node_type', 'concept_category', 'display_name', 'description', 'attributes', 'created_at', 'updated_at']
        assert all(col in columns for col in expected_columns)

        # 验证ontology_edges表存在且有正确字段
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ontology_edges'")
        assert cursor.fetchone() is not None

        cursor.execute("PRAGMA table_info(ontology_edges)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = ['id', 'parent_id', 'child_id', 'relation_type', 'edge_weight', 'created_at']
        assert all(col in columns for col in expected_columns)

        # 验证索引存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_nodes_name'")
        assert cursor.fetchone() is not None

        conn.close()
    finally:
        os.unlink(db_path)


def test_drop_ontology_tables():
    """测试本体表删除"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        drop_ontology_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ontology_nodes'")
        assert cursor.fetchone() is None
        conn.close()
    finally:
        os.unlink(db_path)
