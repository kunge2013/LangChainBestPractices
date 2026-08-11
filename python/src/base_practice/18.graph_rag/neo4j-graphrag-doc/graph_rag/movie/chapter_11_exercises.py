# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第十一部分：完整练习案例
综合查询场景和更新场景
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def query_scenarios():
    """
    11.1 查询场景
    """
    print("\n  --- 11.1 查询场景 ---")

    # 场景1：查找与 Christopher Nolan 合作过的所有演员
    query = """
    MATCH (director:Person {name: 'Christopher Nolan'})-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(actor:Person)
    RETURN DISTINCT actor.name AS 合作演员
    ORDER BY actor.name
    """
    results = Neo4jConnection.execute_query(query)
    print_results("场景1: 与 Christopher Nolan 合作过的所有演员", results)

    # 场景2：查找评分最高的电影及其主创信息
    query = """
    MATCH (m:Movie)
    WITH max(m.rating) AS maxRating
    MATCH (m:Movie)
    WHERE m.rating = maxRating
    OPTIONAL MATCH (p:Person)-[:ACTED_IN]->(m)
    OPTIONAL MATCH (d:Person)-[:DIRECTED]->(m)
    RETURN m.title AS title, m.rating AS rating,
           collect(DISTINCT d.name) AS 导演,
           collect(DISTINCT p.name) AS 演员
    """
    results = Neo4jConnection.execute_query(query)
    print_results("场景2: 评分最高的电影及其主创信息", results)

    # 场景3：演员网络 - 查找与 Leonardo DiCaprio 有共同演员的人
    query = """
    MATCH (leo:Person {name: 'Leonardo DiCaprio'})-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(colleague:Person)
    WHERE colleague <> leo
    MATCH (colleague)-[:ACTED_IN]->(otherMovie:Movie)<-[:ACTED_IN]-(common:Person)
    WHERE common <> leo AND common <> colleague
    RETURN leo.name AS name, colleague.name AS 合作演员,
           common.name AS 共同朋友, otherMovie.title AS 关联电影
    LIMIT 20
    """
    results = Neo4jConnection.execute_query(query)
    print_results("场景3: Leonardo DiCaprio 的演员网络", results)

    # 场景4：查询 Warner Bros. 发行的所有电影及其导演和评分
    query = """
    MATCH (s:Studio {name: 'Warner Bros.'})-[:DISTRIBUTED_BY]->(m:Movie)<-[:DIRECTED]-(d:Person)
    OPTIONAL MATCH (m)<-[:ACTED_IN]-(a:Person)
    RETURN m.title AS 电影, m.rating AS 评分, d.name AS 导演,
           collect(a.name) AS 演员
    ORDER BY m.rating DESC
    """
    results = Neo4jConnection.execute_query(query)
    print_results("场景4: Warner Bros. 发行的电影详情", results)


def update_scenarios():
    """
    11.2 更新场景
    """
    print("\n  --- 11.2 更新场景 ---")

    # 场景1：批量更新 - 为所有评分 > 8.8 的电影添加 'Oscar' 标签
    query = """
    MATCH (m:Movie)
    WHERE m.rating > 8.8
    SET m.award = 'Oscar Nominated'
    RETURN m.title AS title, m.rating AS rating, m.award AS award
    """
    results = Neo4jConnection.execute_write(query)
    print_results("场景1: 高分电影添加 Oscar 标签", results)

    # 场景2：条件更新 - 根据演员数量更新电影热度
    query = """
    MATCH (m:Movie)<-[:ACTED_IN]-(p:Person)
    WITH m, count(p) AS actorCount
    SET m.popularity = CASE
        WHEN actorCount >= 3 THEN 'High'
        WHEN actorCount >= 2 THEN 'Medium'
        ELSE 'Low'
    END
    RETURN m.title AS title, actorCount AS 演员数量, m.popularity AS popularity
    """
    results = Neo4jConnection.execute_write(query)
    print_results("场景2: 根据演员数量更新电影热度", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第十一部分：完整练习案例")
    print("="*80)

    try:
        query_scenarios()
        update_scenarios()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
