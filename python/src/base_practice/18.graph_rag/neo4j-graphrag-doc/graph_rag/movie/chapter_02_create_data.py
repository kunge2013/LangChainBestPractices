# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
第二部分：创建数据（节点 + 关系）
创建电影、人物、制片厂节点以及它们之间的关系
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, print_results


# [AGC:START] tool=Cc author=fangkun
def create_movie_nodes():
    """
    2.1 创建电影节点
    """
    print("\n  --- 2.1 创建电影节点 ---")

    movies = [
        {
            "title": "Inception",
            "released": 2010,
            "rating": 8.8,
            "tagline": "Your mind is the scene of the crime"
        },
        {
            "title": "The Dark Knight",
            "released": 2008,
            "rating": 9.0,
            "tagline": "Why so serious?"
        },
        {
            "title": "Interstellar",
            "released": 2014,
            "rating": 8.6,
            "tagline": "Mankind was born on Earth. It was never meant to die here."
        }
    ]

    for movie in movies:
        query = """
        MERGE (m:Movie {title: $title})
        ON CREATE SET m.released = $released, m.rating = $rating, m.tagline = $tagline
        """
        Neo4jConnection.execute_write(query, movie)
        print(f"  [OK] 创建电影: {movie['title']}")


def create_person_nodes():
    """
    2.2 创建人物节点
    """
    print("\n  --- 2.2 创建人物节点 ---")

    persons = [
        # 演员
        {"name": "Leonardo DiCaprio", "born": 1974, "gender": "Male"},
        {"name": "Christian Bale", "born": 1974, "gender": "Male"},
        {"name": "Matthew McConaughey", "born": 1969, "gender": "Male"},
        {"name": "Anne Hathaway", "born": 1982, "gender": "Female"},
        # 导演
        {"name": "Christopher Nolan", "born": 1970, "gender": "Male"},
        # 演员（小角色）
        {"name": "Michael Caine", "born": 1933, "gender": "Male"}
    ]

    for person in persons:
        query = """
        MERGE (p:Person {name: $name})
        ON CREATE SET p.born = $born, p.gender = $gender
        """
        Neo4jConnection.execute_write(query, person)
        print(f"  [OK] 创建人物: {person['name']}")


def create_studio_nodes():
    """
    2.3 创建制片厂节点
    """
    print("\n  --- 2.3 创建制片厂节点 ---")

    studios = [
        {"name": "Warner Bros.", "country": "USA"},
        {"name": "Paramount Pictures", "country": "USA"},
        {"name": "Legendary Pictures", "country": "USA"}
    ]

    for studio in studios:
        query = """
        MERGE (s:Studio {name: $name})
        ON CREATE SET s.country = $country
        """
        Neo4jConnection.execute_write(query, studio)
        print(f"  [OK] 创建制片厂: {studio['name']}")


def create_relationships():
    """
    2.4 创建关系
    """
    print("\n  --- 2.4 创建关系 ---")

    relationships = [
        # ----- Inception (2010) 的关系 -----
        # 演员
        ("""
        MATCH (p:Person {name: 'Leonardo DiCaprio'}), (m:Movie {title: 'Inception'})
        MERGE (p)-[:ACTED_IN {roles: ['Cobb']}]->(m)
        """, "Leonardo DiCaprio -> Inception (Cobb)"),

        ("""
        MATCH (p:Person {name: 'Michael Caine'}), (m:Movie {title: 'Inception'})
        MERGE (p)-[:ACTED_IN {roles: ['Miles']}]->(m)
        """, "Michael Caine -> Inception (Miles)"),

        # 导演 & 编剧
        ("""
        MATCH (p:Person {name: 'Christopher Nolan'}), (m:Movie {title: 'Inception'})
        MERGE (p)-[:DIRECTED]->(m)
        """, "Christopher Nolan -DIRECTED-> Inception"),

        ("""
        MATCH (p:Person {name: 'Christopher Nolan'}), (m:Movie {title: 'Inception'})
        MERGE (p)-[:WROTE]->(m)
        """, "Christopher Nolan -WROTE-> Inception"),

        # 发行
        ("""
        MATCH (s:Studio {name: 'Warner Bros.'}), (m:Movie {title: 'Inception'})
        MERGE (s)-[:DISTRIBUTED_BY {year: 2010}]->(m)
        """, "Warner Bros. -DISTRIBUTED_BY-> Inception"),

        # ----- The Dark Knight (2008) 的关系 -----
        # 演员
        ("""
        MATCH (p:Person {name: 'Christian Bale'}), (m:Movie {title: 'The Dark Knight'})
        MERGE (p)-[:ACTED_IN {roles: ['Bruce Wayne']}]->(m)
        """, "Christian Bale -> The Dark Knight (Bruce Wayne)"),

        ("""
        MATCH (p:Person {name: 'Michael Caine'}), (m:Movie {title: 'The Dark Knight'})
        MERGE (p)-[:ACTED_IN {roles: ['Alfred']}]->(m)
        """, "Michael Caine -> The Dark Knight (Alfred)"),

        # 导演 & 编剧
        ("""
        MATCH (p:Person {name: 'Christopher Nolan'}), (m:Movie {title: 'The Dark Knight'})
        MERGE (p)-[:DIRECTED]->(m)
        """, "Christopher Nolan -DIRECTED-> The Dark Knight"),

        ("""
        MATCH (p:Person {name: 'Christopher Nolan'}), (m:Movie {title: 'The Dark Knight'})
        MERGE (p)-[:WROTE]->(m)
        """, "Christopher Nolan -WROTE-> The Dark Knight"),

        # 发行
        ("""
        MATCH (s:Studio {name: 'Warner Bros.'}), (m:Movie {title: 'The Dark Knight'})
        MERGE (s)-[:DISTRIBUTED_BY {year: 2008}]->(m)
        """, "Warner Bros. -DISTRIBUTED_BY-> The Dark Knight"),

        ("""
        MATCH (s:Studio {name: 'Legendary Pictures'}), (m:Movie {title: 'The Dark Knight'})
        MERGE (s)-[:DISTRIBUTED_BY {year: 2008}]->(m)
        """, "Legendary Pictures -DISTRIBUTED_BY-> The Dark Knight"),

        # ----- Interstellar (2014) 的关系 -----
        # 演员
        ("""
        MATCH (p:Person {name: 'Matthew McConaughey'}), (m:Movie {title: 'Interstellar'})
        MERGE (p)-[:ACTED_IN {roles: ['Cooper']}]->(m)
        """, "Matthew McConaughey -> Interstellar (Cooper)"),

        ("""
        MATCH (p:Person {name: 'Anne Hathaway'}), (m:Movie {title: 'Interstellar'})
        MERGE (p)-[:ACTED_IN {roles: ['Brand']}]->(m)
        """, "Anne Hathaway -> Interstellar (Brand)"),

        ("""
        MATCH (p:Person {name: 'Michael Caine'}), (m:Movie {title: 'Interstellar'})
        MERGE (p)-[:ACTED_IN {roles: ['Professor Brand']}]->(m)
        """, "Michael Caine -> Interstellar (Professor Brand)"),

        # 导演 & 编剧
        ("""
        MATCH (p:Person {name: 'Christopher Nolan'}), (m:Movie {title: 'Interstellar'})
        MERGE (p)-[:DIRECTED]->(m)
        """, "Christopher Nolan -DIRECTED-> Interstellar"),

        ("""
        MATCH (p:Person {name: 'Christopher Nolan'}), (m:Movie {title: 'Interstellar'})
        MERGE (p)-[:WROTE]->(m)
        """, "Christopher Nolan -WROTE-> Interstellar"),

        # 发行
        ("""
        MATCH (s:Studio {name: 'Warner Bros.'}), (m:Movie {title: 'Interstellar'})
        MERGE (s)-[:DISTRIBUTED_BY {year: 2014}]->(m)
        """, "Warner Bros. -DISTRIBUTED_BY-> Interstellar"),

        ("""
        MATCH (s:Studio {name: 'Paramount Pictures'}), (m:Movie {title: 'Interstellar'})
        MERGE (s)-[:DISTRIBUTED_BY {year: 2014}]->(m)
        """, "Paramount Pictures -DISTRIBUTED_BY-> Interstellar")
    ]

    for query, desc in relationships:
        Neo4jConnection.execute_write(query)
        print(f"  [OK] {desc}")


def verify_data():
    """
    2.5 验证数据
    """
    print("\n  --- 2.5 验证数据 ---")

    # 查看所有节点
    query = "MATCH (n) RETURN n"
    results = Neo4jConnection.execute_query(query)
    print_results("所有节点", results)

    # 查看所有关系
    query = "MATCH ()-[r]->() RETURN r"
    results = Neo4jConnection.execute_query(query)
    print_results("所有关系", results)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  第二部分：创建数据（节点 + 关系）")
    print("="*80)

    try:
        create_movie_nodes()
        create_person_nodes()
        create_studio_nodes()
        create_relationships()
        verify_data()
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        raise
    finally:
        Neo4jConnection.close()


if __name__ == "__main__":
    main()
# [AGC:END]
