# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
本体数据库表结构定义
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def init_ontology_tables(db_path: str) -> None:
    """
    初始化本体表结构

    创建 ontology_nodes 和 ontology_edges 表以及必要的索引
    """
    # [AGC:START] tool=Cc author=fangkun
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 创建 ontology_nodes 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ontology_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_name TEXT NOT NULL UNIQUE,
                node_type TEXT NOT NULL,
                concept_category TEXT NOT NULL,
                display_name TEXT,
                description TEXT,
                attributes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建 ontology_edges 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ontology_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER NOT NULL,
                child_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                edge_weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES ontology_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (child_id) REFERENCES ontology_nodes(id) ON DELETE CASCADE,
                UNIQUE(parent_id, child_id, relation_type)
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_name ON ontology_nodes(node_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_type ON ontology_nodes(node_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_category ON ontology_nodes(concept_category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_parent ON ontology_edges(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_child ON ontology_edges(child_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_relation ON ontology_edges(relation_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_parent_child ON ontology_edges(parent_id, child_id)')

        conn.commit()
        logger.info(f"本体表初始化完成: {db_path}")

    except Exception as e:
        conn.rollback()
        logger.error(f"本体表初始化失败: {e}")
        raise
    finally:
        conn.close()
    # [AGC:END]


def drop_ontology_tables(db_path: str) -> None:
    """
    删除本体表结构

    用于测试清理或重建
    """
    # [AGC:START] tool=Cc author=fangkun
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 删除表（索引会自动删除）
        cursor.execute('DROP TABLE IF EXISTS ontology_edges')
        cursor.execute('DROP TABLE IF EXISTS ontology_nodes')

        conn.commit()
        logger.info(f"本体表已删除: {db_path}")

    except Exception as e:
        conn.rollback()
        logger.error(f"本体表删除失败: {e}")
        raise
    finally:
        conn.close()
    # [AGC:END]
