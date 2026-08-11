# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第六部分：聚合查询（统计）
包括 count、collect、avg、min、max 等聚合函数
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def aggregation_queries():
    """
    聚合查询示例
    """
    # 1. 统计每个导演的电影数量
    query = """
    MATCH (p:Person)-[:DIRECTED]->(m:Movie)
    RETURN p.name AS 导演, count(m) AS 电影数量
    ORDER BY count(m) DESC
    """
    results = Neo4jConnection.execute_query(query)
    print_results("每个导演的电影数量", results)

    # 2. 统计每个演员出演的电影数量
    query = """
    MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
    RETURN p.name AS 演员, count(m) AS 出演电影数
    ORDER BY count(m) DESC
    """
    results = Neo4jConnection.execute_query(query)
    print_results("每个演员出演的电影数量", results)

    # 3. 统计每部电影的演员数量
    query = """
    MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
    RETURN m.title AS 电影, count(p) AS 演员数量
    """
    results = Neo4jConnection.execute_query(query)
    print_results("每部电影的演员数量", results)

    # 4. 统计每个制片厂发行的电影数量
    query = """
    MATCH (s:Studio)-[:DISTRIBUTED_BY]->(m:Movie)
    RETURN s.name AS 制片厂, count(m) AS 电影数量
    """
    results = Neo4jConnection.execute_query(query)
    print_results("每个制片厂发行的电影数量", results)

    # 5. 计算所有电影的平均评分
    query = """
    MATCH (m:Movie)
    RETURN avg(m.rating) AS 平均评分, min(m.rating) AS 最低分, max(m.rating) AS 最高分
    """
    results = Neo4jConnection.execute_query(query)
    print_results("电影评分统计", results)

    # 6. 每年上映的电影数量
    query = """
    MATCH (m:Movie)
    RETURN m.released AS 年份, count(m) AS 电影数量
    ORDER BY m.released
    """
    results = Neo4jConnection.execute_query(query)
    print_results("每年上映的电影数量", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第六部分：聚合查询（统计）")
    print("="*80)

    try:
        aggregation_queries()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
