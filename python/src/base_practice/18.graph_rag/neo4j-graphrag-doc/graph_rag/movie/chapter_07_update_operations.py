# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第七部分：更新操作（SET）
包括更新节点属性、关系属性、条件更新
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def update_node_properties():
    """
    7.1 更新节点属性
    """
    print("\n  --- 7.1 更新节点属性 ---")

    # 1. 更新单个属性
    query = """
    MATCH (m:Movie {title: 'Inception'})
    SET m.rating = 9.0
    RETURN m.title AS title, m.rating AS rating
    """
    results = Neo4jConnection.execute_write(query)
    print_results("更新单个属性 (Inception rating)", results)

    # 2. 更新多个属性
    query = """
    MATCH (m:Movie {title: 'Inception'})
    SET m.rating = 8.8, m.budget = 160000000
    RETURN m
    """
    results = Neo4jConnection.execute_write(query)
    print_results("更新多个属性 (Inception rating + budget)", results)

    # 3. 添加新属性
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})
    SET p.nationality = 'British'
    RETURN p
    """
    results = Neo4jConnection.execute_write(query)
    print_results("添加新属性 (Nolan nationality)", results)

    # 4. 更新人物（使用 ON CREATE 和 ON MATCH）
    query = """
    MERGE (p:Person {name: 'Leonardo DiCaprio'})
    ON CREATE SET p.born = 1974
    ON MATCH SET p.lastUpdated = date()
    RETURN p
    """
    results = Neo4jConnection.execute_write(query)
    print_results("ON CREATE / ON MATCH 更新", results)


def update_relationship_properties():
    """
    7.2 更新关系属性
    """
    print("\n  --- 7.2 更新关系属性 ---")

    # 1. 更新关系属性
    query = """
    MATCH (s:Studio {name: 'Warner Bros.'})-[r:DISTRIBUTED_BY]->(m:Movie {title: 'Inception'})
    SET r.year = 2010, r.region = 'Worldwide'
    RETURN r
    """
    results = Neo4jConnection.execute_write(query)
    print_results("更新关系属性 (DISTRIBUTED_BY)", results)

    # 2. 添加关系属性
    query = """
    MATCH (p:Person {name: 'Leonardo DiCaprio'})-[r:ACTED_IN]->(m:Movie {title: 'Inception'})
    SET r.salary = 20000000
    RETURN r
    """
    results = Neo4jConnection.execute_write(query)
    print_results("添加关系属性 (ACTED_IN salary)", results)


def conditional_updates():
    """
    7.3 条件更新（CASE WHEN）
    """
    print("\n  --- 7.3 条件更新 ---")

    # 1. 根据条件更新评分
    query = """
    MATCH (m:Movie)
    SET m.rating_category = CASE
        WHEN m.rating >= 9.0 THEN 'Excellent'
        WHEN m.rating >= 8.5 THEN 'Good'
        ELSE 'Average'
    END
    RETURN m.title AS title, m.rating AS rating, m.rating_category AS rating_category
    """
    results = Neo4jConnection.execute_write(query)
    print_results("根据条件更新评分类别", results)

    # 2. 根据上映年份添加标签
    query = """
    MATCH (m:Movie)
    SET m.era = CASE
        WHEN m.released < 2010 THEN 'Classic'
        ELSE 'Modern'
    END
    RETURN m.title AS title, m.released AS released, m.era AS era
    """
    results = Neo4jConnection.execute_write(query)
    print_results("根据上映年份添加时代标签", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第七部分：更新操作（SET）")
    print("="*80)

    try:
        update_node_properties()
        update_relationship_properties()
        conditional_updates()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
