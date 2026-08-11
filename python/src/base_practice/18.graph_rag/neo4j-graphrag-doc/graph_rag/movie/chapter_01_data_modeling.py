# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第一部分：数据建模（实体-关系-属性）
创建约束（保证数据唯一性）
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def create_constraints():
    """
    创建数据模型约束
    """
    print("\n" + "="*80)
    print("  第一部分：数据建模（创建约束）")
    print("="*80)

    # 数据模型设计
    print("\n  --- 数据模型设计 ---")
    print("""
    实体（节点）：
    - Movie（电影）：title, released, rating, tagline
    - Person（人物）：name, born, gender
    - Studio（制片厂）：name, country

    关系（Relationship）：
    - ACTED_IN（出演）：roles（角色列表）
    - DIRECTED（导演）：无属性
    - PRODUCED（制片）：无属性
    - WROTE（编剧）：无属性
    - DISTRIBUTED_BY（发行）：year（发行年份）
    """)

    # 1. 创建唯一性约束
    print("\n  --- 创建唯一性约束 ---")

    constraints = [
        # 电影标题唯一约束
        {
            "name": "movie_title_unique",
            "cypher": """
                CREATE CONSTRAINT movie_title_unique IF NOT EXISTS
                FOR (m:Movie) REQUIRE m.title IS UNIQUE
            """
        },
        # 人物名称唯一约束
        {
            "name": "person_name_unique",
            "cypher": """
                CREATE CONSTRAINT person_name_unique IF NOT EXISTS
                FOR (p:Person) REQUIRE p.name IS UNIQUE
            """
        },
        # 制片厂名称唯一约束
        {
            "name": "studio_name_unique",
            "cypher": """
                CREATE CONSTRAINT studio_name_unique IF NOT EXISTS
                FOR (s:Studio) REQUIRE s.name IS UNIQUE
            """
        }
    ]

    for constraint in constraints:
        try:
            Neo4jConnection.execute_write(constraint["cypher"])
            print(f"  [OK] 约束 '{constraint['name']}' 创建成功")
        except Exception as e:
            print(f"  [WARN] 约束 '{constraint['name']}' 已存在或创建失败: {e}")

    # 2. 查看已创建的约束
    print("\n  --- 查看已创建的约束 ---")
    show_constraints = "SHOW CONSTRAINTS"
    results = Neo4jConnection.execute_query(show_constraints)
    print_results("已创建的约束", results)


def main():
    """主函数"""
    try:
        create_constraints()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
