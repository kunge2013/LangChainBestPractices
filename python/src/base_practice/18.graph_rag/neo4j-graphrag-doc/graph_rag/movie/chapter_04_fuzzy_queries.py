# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第四部分：模糊查询
包括 CONTAINS、STARTS WITH、ENDS WITH 和正则表达式查询
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def string_pattern_queries():
    """
    4.1 使用 CONTAINS、STARTS WITH、ENDS WITH
    """
    print("\n  --- 4.1 使用 CONTAINS、STARTS WITH、ENDS WITH ---")

    # 1. 查询标题包含 'dark' 的电影（不区分大小写）
    query = """
    MATCH (m:Movie)
    WHERE toLower(m.title) CONTAINS 'dark'
    RETURN m.title AS title
    """
    results = Neo4jConnection.execute_query(query)
    print_results("标题包含 'dark' 的电影", results)

    # 2. 查询以 'The' 开头的电影
    query = """
    MATCH (m:Movie)
    WHERE m.title STARTS WITH 'The'
    RETURN m.title AS title
    """
    results = Neo4jConnection.execute_query(query)
    print_results("以 'The' 开头的电影", results)

    # 3. 查询名字以 'Leon' 开头的人物
    query = """
    MATCH (p:Person)
    WHERE p.name STARTS WITH 'Leon'
    RETURN p.name AS name
    """
    results = Neo4jConnection.execute_query(query)
    print_results("名字以 'Leon' 开头的人物", results)

    # 4. 查询名字包含 'nolan' 的人物
    query = """
    MATCH (p:Person)
    WHERE toLower(p.name) CONTAINS 'nolan'
    RETURN p.name AS name
    """
    results = Neo4jConnection.execute_query(query)
    print_results("名字包含 'nolan' 的人物", results)


def regex_queries():
    """
    4.2 使用正则表达式
    """
    print("\n  --- 4.2 使用正则表达式 ---")

    # 1. 查询名字包含 'a' 且以 'e' 结尾的人物
    query = """
    MATCH (p:Person)
    WHERE p.name =~ '.*a.*e$'
    RETURN p.name AS name
    """
    results = Neo4jConnection.execute_query(query)
    print_results("名字包含 'a' 且以 'e' 结尾的人物", results)

    # 2. 查询名字以 'C' 或 'L' 开头的人物（不区分大小写）
    query = """
    MATCH (p:Person)
    WHERE p.name =~ '(?i)^[CL].*'
    RETURN p.name AS name
    """
    results = Neo4jConnection.execute_query(query)
    print_results("名字以 'C' 或 'L' 开头的人物", results)

    # 3. 查询评分包含 .8 的电影（如 8.8, 9.8）
    query = """
    MATCH (m:Movie)
    WHERE toString(m.rating) =~ '.*\\.8$'
    RETURN m.title AS title, m.rating AS rating
    """
    results = Neo4jConnection.execute_query(query)
    print_results("评分以 .8 结尾的电影", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第四部分：模糊查询")
    print("="*80)

    try:
        string_pattern_queries()
        regex_queries()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
