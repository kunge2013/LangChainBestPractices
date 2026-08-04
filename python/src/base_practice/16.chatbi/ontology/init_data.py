# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
示例数据加载器
"""

# [AGC:START] tool=Cc author=fangkun
import sqlite3
import logging

logger = logging.getLogger(__name__)


def load_sample_ontology_data(db_path: str) -> None:
    """
    加载示例本体数据

    参数:
        db_path: 数据库路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 清空现有数据
        cursor.execute("DELETE FROM ontology_edges")
        cursor.execute("DELETE FROM ontology_nodes")

        # ========== 城市分类（两级结构）==========
        # 抽象概念
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
            VALUES (?, 'abstract_concept', 'city', ?)
        """, [
            ('tier1_cities', '一线城市'),
            ('tier2_cities', '新一线城市'),
        ])

        # 具体实例
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES (?, 'concrete_instance', 'city', ?, ?)
        """, [
            ('shanghai', '上海', '{"code": "021", "tier": "1"}'),
            ('beijing', '北京', '{"code": "010", "tier": "1"}'),
            ('guangzhou', '广州', '{"code": "020", "tier": "1"}'),
            ('shenzhen', '深圳', '{"code": "0755", "tier": "1"}'),
            ('hangzhou', '杭州', '{"code": "0571", "tier": "2"}'),
            ('chengdu', '成都', '{"code": "028", "tier": "2"}'),
            ('wuhan', '武汉', '{"code": "027", "tier": "2"}'),
        ])

        # 建立关系：一线城市
        tier1_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier1_cities'").fetchone()[0]
        for city in ['shanghai', 'beijing', 'guangzhou', 'shenzhen']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (tier1_id, city_id))

        # 建立关系：新一线城市
        tier2_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier2_cities'").fetchone()[0]
        for city in ['hangzhou', 'chengdu', 'wuhan']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (tier2_id, city_id))

        # ========== 客户分类（三级结构）==========
        # 抽象概念
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
            VALUES (?, 'abstract_concept', 'customer', ?)
        """, [
            ('bytedance_group', '字节跳动集团'),
            ('wuhan_subsidiaries', '武汉子公司'),
        ])

        # 具体实例
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
            VALUES (?, 'concrete_instance', 'customer', ?)
        """, [
            ('wuhan_toutiao', '武汉今日头条'),
            ('wuhan_douyin', '武汉抖音'),
            ('wuhan_feishu', '武汉飞书'),
        ])

        # 建立关系：字节跳动集团 -> 武汉子公司
        group_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'bytedance_group'").fetchone()[0]
        subs_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'wuhan_subsidiaries'").fetchone()[0]
        cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                      (group_id, subs_id))

        # 建立关系：武汉子公司 -> 具体公司
        for company in ['wuhan_toutiao', 'wuhan_douyin', 'wuhan_feishu']:
            company_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (company,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (subs_id, company_id))

        # ========== 区域分类（两级结构）==========
        # 抽象概念
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
            VALUES (?, 'abstract_concept', 'region', ?)
        """, [
            ('east_china', '华东区'),
            ('central_china', '华中区'),
        ])

        # 具体实例（使用 INSERT OR IGNORE 避免与城市分类重复）
        cursor.executemany("""
            INSERT OR IGNORE INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES (?, 'concrete_instance', 'region', ?, ?)
        """, [
            ('shanghai', '上海', '{"code": "SH", "level": "city"}'),
            ('hangzhou', '杭州', '{"code": "HZ", "level": "city"}'),
            ('nanjing', '南京', '{"code": "NJ", "level": "city"}'),
            ('suzhou', '苏州', '{"code": "SZ", "level": "city"}'),
            ('wuhan', '武汉', '{"code": "WH", "level": "city"}'),
            ('changsha', '长沙', '{"code": "CS", "level": "city"}'),
            ('zhengzhou', '郑州', '{"code": "ZZ", "level": "city"}'),
        ])

        # 建立关系：华东区
        east_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'east_china'").fetchone()[0]
        for city in ['shanghai', 'hangzhou', 'nanjing', 'suzhou']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (east_id, city_id))

        # 建立关系：华中区
        central_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'central_china'").fetchone()[0]
        for city in ['wuhan', 'changsha', 'zhengzhou']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (central_id, city_id))

        conn.commit()
        logger.info(f"示例本体数据加载完成: {db_path}")

    except Exception as e:
        conn.rollback()
        logger.error(f"示例数据加载失败: {e}")
        raise
    finally:
        conn.close()
# [AGC:END]
