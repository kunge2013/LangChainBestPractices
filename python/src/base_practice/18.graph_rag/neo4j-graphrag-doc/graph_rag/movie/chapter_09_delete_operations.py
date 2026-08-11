# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第九部分：删除操作
包括删除属性、删除关系、删除节点
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def setup_test_data():
    """
    准备测试数据
    """
    print("\n  --- 准备测试数据 ---")
    query = """
    MERGE (m:Movie {title: 'Test Movie'})
    ON CREATE SET m.released = 2020, m.rating = 7.0
    MERGE (p:Person {name: 'Test Person'})
    ON CREATE SET p.born = 1990
    MERGE (p)-[:ACTED_IN {roles: ['Test Role']}]->(m)
    """
    Neo4jConnection.execute_write(query)
    print("  [OK] 测试数据已创建")


def delete_properties():
    """
    9.1 删除属性
    """
    print("\n  --- 9.1 删除属性 ---")

    # 1. 删除节点属性
    query = """
    MATCH (m:Movie {title: 'Inception'})
    REMOVE m.budget
    RETURN m
    """
    results = Neo4jConnection.execute_write(query)
    print_results("删除节点属性 (budget)", results)

    # 2. 删除关系属性
    query = """
    MATCH (p:Person {name: 'Leonardo DiCaprio'})-[r:ACTED_IN]->(m:Movie {title: 'Inception'})
    REMOVE r.salary
    RETURN r
    """
    results = Neo4jConnection.execute_write(query)
    print_results("删除关系属性 (salary)", results)


def delete_relationships():
    """
    9.2 删除关系
    """
    print("\n  --- 9.2 删除关系 ---")

    # 1. 删除特定关系
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})-[r:PRODUCED]->(m:Movie {title: 'Inception'})
    DELETE r
    """
    Neo4jConnection.execute_write(query)
    print("  [OK] Christopher Nolan -PRODUCED-> Inception 关系已删除")

    # 验证删除
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})-[r:PRODUCED]->(m:Movie {title: 'Inception'})
    RETURN r
    """
    results = Neo4jConnection.execute_query(query)
    print_results("验证 PRODUCED 关系已删除", results)

    # 2. 删除测试关系
    query = """
    MATCH (p:Person {name: 'Test Person'})-[r:ACTED_IN]->(m:Movie {title: 'Test Movie'})
    DELETE r
    """
    Neo4jConnection.execute_write(query)
    print("  [OK] 测试关系已删除")


def delete_nodes():
    """
    9.3 删除节点
    """
    print("\n  --- 9.3 删除节点 ---")

    # 1. 删除孤立节点（DETACH DELETE 会先删除关系）
    query = """
    MATCH (p:Person {name: 'Test Person'})
    DETACH DELETE p
    """
    Neo4jConnection.execute_write(query)
    print("  [OK] Test Person 节点已删除")

    # 2. 删除特定条件的节点
    query = """
    MATCH (m:Movie {title: 'Test Movie'})
    DETACH DELETE m
    """
    Neo4jConnection.execute_write(query)
    print("  [OK] Test Movie 节点已删除")

    # 验证删除
    query = "MATCH (n) WHERE n.name = 'Test Person' OR n.title = 'Test Movie' RETURN n"
    results = Neo4jConnection.execute_query(query)
    print_results("验证测试数据已删除", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第九部分：删除操作")
    print("="*80)

    try:
        setup_test_data()
        delete_properties()
        delete_relationships()
        delete_nodes()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
