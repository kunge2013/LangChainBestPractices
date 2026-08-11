# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第五部分：关系查询（核心）
包括单层关系查询、带关系属性的查询、多层关系查询、路径查询
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def single_level_relationship_queries():
    """
    5.1 单层关系查询
    """
    print("\n  --- 5.1 单层关系查询 ---")

    # 1. 查询 Inception 的演员
    query = """
    MATCH (p:Person)-[:ACTED_IN]->(m:Movie {title: 'Inception'})
    RETURN p.name AS 演员, p.born AS 出生年份
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Inception 的演员", results)

    # 2. 查询 Inception 的导演
    query = """
    MATCH (p:Person)-[:DIRECTED]->(m:Movie {title: 'Inception'})
    RETURN p.name AS 导演
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Inception 的导演", results)

    # 3. 查询所有导演及其电影
    query = """
    MATCH (p:Person)-[:DIRECTED]->(m:Movie)
    RETURN p.name AS 导演, collect(m.title) AS 导演作品
    """
    results = Neo4jConnection.execute_query(query)
    print_results("所有导演及其电影", results)

    # 4. 查询 Leonardo DiCaprio 演过哪些电影
    query = """
    MATCH (p:Person {name: 'Leonardo DiCaprio'})-[:ACTED_IN]->(m:Movie)
    RETURN m.title AS 电影, m.released AS 上映年份
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Leonardo DiCaprio 演过的电影", results)

    # 5. 查询 Christopher Nolan 导演的所有电影
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})-[:DIRECTED]->(m:Movie)
    RETURN m.title AS title, m.released AS released, m.rating AS rating
    ORDER BY m.released DESC
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Christopher Nolan 导演的所有电影", results)


def relationship_property_queries():
    """
    5.2 带关系属性的查询
    """
    print("\n  --- 5.2 带关系属性的查询 ---")

    # 1. 查询 Inception 中所有演员及其角色
    query = """
    MATCH (p:Person)-[r:ACTED_IN]->(m:Movie {title: 'Inception'})
    RETURN p.name AS 演员, r.roles AS 角色
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Inception 中所有演员及其角色", results)

    # 2. 查询 Warner Bros. 发行的所有电影及发行年份
    query = """
    MATCH (s:Studio {name: 'Warner Bros.'})-[r:DISTRIBUTED_BY]->(m:Movie)
    RETURN m.title AS 电影, r.year AS 发行年份
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Warner Bros. 发行的所有电影及发行年份", results)

    # 3. 查询特定角色（如 'Cooper'）
    query = """
    MATCH (p:Person)-[:ACTED_IN {roles: ['Cooper']}]->(m:Movie)
    RETURN p.name AS name, m.title AS title
    """
    results = Neo4jConnection.execute_query(query)
    print_results("饰演 'Cooper' 的演员", results)


def multi_level_relationship_queries():
    """
    5.3 多层关系查询（重要！）
    """
    print("\n  --- 5.3 多层关系查询 ---")

    # 1. 查询与 Leonardo DiCaprio 合作过的其他演员
    query = """
    MATCH (p1:Person {name: 'Leonardo DiCaprio'})-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(p2:Person)
    WHERE p1 <> p2
    RETURN p2.name AS 合作演员, collect(m.title) AS 共同出演电影
    """
    results = Neo4jConnection.execute_query(query)
    print_results("与 Leonardo DiCaprio 合作过的其他演员", results)

    # 2. 查询 Christopher Nolan 合作过的所有演员
    query = """
    MATCH (director:Person {name: 'Christopher Nolan'})-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(actor:Person)
    RETURN DISTINCT actor.name AS 演员, count(m) AS 合作电影数
    ORDER BY count(m) DESC
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Christopher Nolan 合作过的所有演员", results)

    # 3. 查询 Warner Bros. 发行的电影的所有导演
    query = """
    MATCH (s:Studio {name: 'Warner Bros.'})-[:DISTRIBUTED_BY]->(m:Movie)<-[:DIRECTED]-(p:Person)
    RETURN p.name AS 导演, collect(m.title) AS 电影
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Warner Bros. 发行的电影的所有导演", results)

    # 4. 查询导演 Christopher Nolan 电影的制片厂
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})-[:DIRECTED]->(m:Movie)<-[:DISTRIBUTED_BY]-(s:Studio)
    RETURN DISTINCT s.name AS 发行公司
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Christopher Nolan 电影的发行公司", results)


def path_queries():
    """
    5.4 路径查询（Path）
    """
    print("\n  --- 5.4 路径查询 ---")

    # 1. 查询 Christopher Nolan 到 Leonardo DiCaprio 的路径
    query = """
    MATCH p = (n1:Person {name: 'Christopher Nolan'})-[*1..3]-(n2:Person {name: 'Leonardo DiCaprio'})
    RETURN p
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Christopher Nolan 到 Leonardo DiCaprio 的路径", results)

    # 2. 查询最短路径
    query = """
    MATCH p = shortestPath((n1:Person {name: 'Christopher Nolan'})-[*]-(n2:Person {name: 'Leonardo DiCaprio'}))
    RETURN p
    """
    results = Neo4jConnection.execute_query(query)
    print_results("Christopher Nolan 到 Leonardo DiCaprio 的最短路径", results)

    # 3. 查询所有长度为 2 的路径（导演-电影-演员）
    query = """
    MATCH p = (n1:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(n2:Person)
    RETURN n1.name AS 导演, m.title AS 电影, n2.name AS 演员
    LIMIT 10
    """
    results = Neo4jConnection.execute_query(query)
    print_results("导演-电影-演员 路径", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第五部分：关系查询（核心）")
    print("="*80)

    try:
        single_level_relationship_queries()
        relationship_property_queries()
        multi_level_relationship_queries()
        path_queries()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
