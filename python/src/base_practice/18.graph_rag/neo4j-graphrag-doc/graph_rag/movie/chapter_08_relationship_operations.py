# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第八部分：插入和更新关系
包括插入新关系、安全创建关系、批量插入、更新关系
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def insert_relationships():
    """
    8.1 插入新关系
    """
    print("\n  --- 8.1 插入新关系 ---")

    # 1. 为已有节点创建新关系
    query = """
    MATCH (p:Person {name: 'Michael Caine'})
    MATCH (m:Movie {title: 'Inception'})
    MERGE (p)-[:ACTED_IN {roles: ['Miles']}]->(m)
    """
    Neo4jConnection.execute_write(query)
    print("  [OK] Michael Caine -> Inception 关系已存在或创建")

    # 2. 创建不存在的关系（安全创建）
    query = """
    MERGE (p:Person {name: 'Christian Bale'})-[r:ACTED_IN {roles: ['Bruce Wayne']}]->(m:Movie {title: 'The Dark Knight'})
    ON CREATE SET r.character = 'Batman'
    RETURN r
    """
    results = Neo4jConnection.execute_write(query)
    print_results("安全创建关系 (Christian Bale -> The Dark Knight)", results)

    # 3. 批量插入关系
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})
    MATCH (m:Movie)
    WHERE m.title IN ['Inception', 'The Dark Knight', 'Interstellar']
    MERGE (p)-[:PRODUCED]->(m)
    """
    Neo4jConnection.execute_write(query)
    print("  [OK] Christopher Nolan -PRODUCED-> 所有电影")

    # 4. 删除旧关系并创建新关系
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})-[r:WROTE]->(m:Movie {title: 'Inception'})
    DELETE r
    WITH m
    MATCH (p:Person {name: 'Christopher Nolan'})
    MERGE (p)-[:CO_WROTE]->(m)
    """
    Neo4jConnection.execute_write(query)
    print("  [OK] WROTE 关系替换为 CO_WROTE")


def update_relationships():
    """
    8.2 更新关系
    """
    print("\n  --- 8.2 更新关系 ---")

    # 1. 更新关系属性
    query = """
    MATCH (p:Person {name: 'Leonardo DiCaprio'})-[r:ACTED_IN]->(m:Movie {title: 'Inception'})
    SET r.roles = ['Dominick Cobb', 'The Extractor']
    RETURN r.roles AS roles
    """
    results = Neo4jConnection.execute_write(query)
    print_results("更新关系属性 (roles)", results)

    # 2. 添加关系属性
    query = """
    MATCH (p:Person {name: 'Christian Bale'})-[r:ACTED_IN]->(m:Movie {title: 'The Dark Knight'})
    SET r.year = 2008, r.character = 'Batman'
    RETURN r
    """
    results = Neo4jConnection.execute_write(query)
    print_results("添加关系属性 (year, character)", results)

    # 3. 批量更新关系属性
    query = """
    MATCH (p:Person)-[r:ACTED_IN]->(m:Movie)
    WHERE m.released > 2010
    SET r.after_2010 = true
    RETURN p.name AS name, m.title AS title, r.after_2010 AS after_2010
    """
    results = Neo4jConnection.execute_write(query)
    print_results("批量更新关系属性 (after_2010)", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第八部分：插入和更新关系")
    print("="*80)

    try:
        insert_relationships()
        update_relationships()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
