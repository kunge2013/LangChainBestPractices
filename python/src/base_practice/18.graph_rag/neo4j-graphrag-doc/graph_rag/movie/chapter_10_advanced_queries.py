# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第十部分：高级查询（综合应用）
包括复杂条件查询、EXISTS 子查询、列表操作
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def complex_condition_queries():
    """
    10.1 复杂条件查询
    """
    print("\n  --- 10.1 复杂条件查询 ---")

    # 1. 查询评分 > 8.5 且上映于 2010 年后的电影
    query = """
    MATCH (m:Movie)
    WHERE m.rating > 8.5 AND m.released >= 2010
    RETURN m.title AS title, m.rating AS rating, m.released AS released
    """
    results = Neo4jConnection.execute_query(query)
    print_results("评分 > 8.5 且上映于 2010 年后的电影", results)

    # 2. 查询 Warner Bros. 发行的高分电影（评分 > 8.8）
    query = """
    MATCH (s:Studio {name: 'Warner Bros.'})-[:DISTRIBUTED_BY]->(m:Movie)
    WHERE m.rating > 8.8
    RETURN m.title AS title, m.rating AS rating
    ORDER BY m.rating DESC
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Warner Bros. 发行的高分电影", results)

    # 3. 查询同时出演 Inception 和 The Dark Knight 的演员
    query = """
    MATCH (p:Person)-[:ACTED_IN]->(m1:Movie {title: 'Inception'})
    MATCH (p)-[:ACTED_IN]->(m2:Movie {title: 'The Dark Knight'})
    RETURN p.name AS 演员
    """
    results = Neo4jConnection.execute_query(query)
    print_results("同时出演 Inception 和 The Dark Knight 的演员", results)

    # 4. 查询与 Christopher Nolan 合作超过 1 次的演员
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(actor:Person)
    WITH actor, count(m) AS movies
    WHERE movies > 1
    RETURN actor.name AS 演员, movies AS 合作次数
    """
    results = Neo4jConnection.execute_query(query)
    print_results("与 Christopher Nolan 合作超过 1 次的演员", results)


def exists_subqueries():
    """
    10.2 EXISTS 子查询
    """
    print("\n  --- 10.2 EXISTS 子查询 ---")

    # 1. 查询有演员出演的电影
    query = """
    MATCH (m:Movie)
    WHERE EXISTS { MATCH (p:Person)-[:ACTED_IN]->(m) }
    RETURN m.title AS title
    """
    results = Neo4jConnection.execute_query(query)
    print_results("有演员出演的电影", results)

    # 2. 查询有资深演员的电影（born < 1960）
    query = """
    MATCH (m:Movie)
    WHERE EXISTS {
        MATCH (p:Person)-[:ACTED_IN]->(m)
        WHERE p.born < 1960
    }
    RETURN m.title AS title
    """
    results = Neo4jConnection.execute_query(query)
    print_results("有资深演员的电影", results)


def list_operations():
    """
    10.3 列表操作
    """
    print("\n  --- 10.3 列表操作 ---")

    # 1. 收集所有演员
    query = """
    MATCH (p:Person)-[:ACTED_IN]->(m:Movie {title: 'Inception'})
    RETURN collect(p.name) AS 演员列表
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Inception 演员列表", results)

    # 2. 展开列表
    query = """
    MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
    RETURN m.title AS title, p.name AS actor
    ORDER BY m.title
    """
    results = Neo4jConnection.execute_query(query)
    print_results("所有电影及其演员", results)

    # 3. 列表去重
    query = """
    MATCH (m:Movie)<-[:ACTED_IN]-(p:Person)
    RETURN m.title AS title, collect(DISTINCT p.name) AS 演员
    """
    results = Neo4jConnection.execute_query(query)
    print_results("每部电影的演员（去重）", results)

    # 4. 列表大小
    query = """
    MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
    WITH m, collect(p.name) AS actors
    WHERE size(actors) > 2
    RETURN m.title AS title, actors AS 演员, size(actors) AS 演员数
    """
    results = Neo4jConnection.execute_query(query)
    print_results("演员数量大于 2 的电影", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第十部分：高级查询（综合应用）")
    print("="*80)

    try:
        complex_condition_queries()
        exists_subqueries()
        list_operations()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
