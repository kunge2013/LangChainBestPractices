# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第三部分：基础查询（简单查询）
包括查询所有数据、精确查询、条件查询
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def query_all_data():
    """
    3.1 查询所有数据
    """
    print("\n  --- 3.1 查询所有数据 ---")

    # 1. 查询所有电影
    query = "MATCH (m:Movie) RETURN m"
    results = Neo4jConnection.execute_query(query)
    print_results("所有电影", results)

    # 2. 查询所有人
    query = "MATCH (p:Person) RETURN p"
    results = Neo4jConnection.execute_query(query)
    print_results("所有人", results)

    # 3. 查询所有制片厂
    query = "MATCH (s:Studio) RETURN s"
    results = Neo4jConnection.execute_query(query)
    print_results("所有制片厂", results)

    # 4. 返回特定属性（投影）
    query = """
    MATCH (m:Movie)
    RETURN m.title AS 电影名称, m.released AS 上映年份, m.rating AS 评分
    """
    results = Neo4jConnection.execute_query(query)
    print_results("电影属性投影", results)


def exact_queries():
    """
    3.2 精确查询
    """
    print("\n  --- 3.2 精确查询 ---")

    # 1. 查询特定电影
    query = "MATCH (m:Movie {title: 'Inception'}) RETURN m"
    results = Neo4jConnection.execute_query(query)
    print_results("查询特定电影 Inception", results)

    # 2. 查询特定人物
    query = """
    MATCH (p:Person {name: 'Christopher Nolan'})
    RETURN p.name AS name, p.born AS born, p.gender AS gender
    """
    results = Neo4jConnection.execute_query(query)
    print_results("查询特定人物 Christopher Nolan", results)

    # 3. 查询特定制片厂
    query = "MATCH (s:Studio {name: 'Warner Bros.'}) RETURN s"
    results = Neo4jConnection.execute_query(query)
    print_results("查询特定制片厂 Warner Bros.", results)


def condition_queries():
    """
    3.3 条件查询（WHERE）
    """
    print("\n  --- 3.3 条件查询 ---")

    # 1. 查询评分大于 8.5 的电影
    query = """
    MATCH (m:Movie)
    WHERE m.rating > 8.5
    RETURN m.title AS title, m.rating AS rating
    ORDER BY m.rating DESC
    """
    results = Neo4jConnection.execute_query(query)
    print_results("评分大于 8.5 的电影", results)

    # 2. 查询 2010 年以后上映的电影
    query = """
    MATCH (m:Movie)
    WHERE m.released >= 2010
    RETURN m.title AS title, m.released AS released
    """
    results = Neo4jConnection.execute_query(query)
    print_results("2010 年以后上映的电影", results)

    # 3. 查询评分在 8.0 到 9.0 之间的电影
    query = """
    MATCH (m:Movie)
    WHERE m.rating >= 8.0 AND m.rating <= 9.0
    RETURN m.title AS title, m.rating AS rating
    """
    results = Neo4jConnection.execute_query(query)
    print_results("评分在 8.0 到 9.0 之间的电影", results)

    # 4. 查询 2000-2010 年间的电影
    query = """
    MATCH (m:Movie)
    WHERE m.released >= 2000 AND m.released <= 2010
    RETURN m.title AS title, m.released AS released
    """
    results = Neo4jConnection.execute_query(query)
    print_results("2000-2010 年间的电影", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第三部分：基础查询（简单查询）")
    print("="*80)

    try:
        query_all_data()
        exact_queries()
        condition_queries()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
