# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
图数据导入逻辑
将电影、人物、制片厂数据及关系导入 Neo4j 数据库
"""
from typing import List, Dict, Any
from data_init import Neo4jConnection
from models import MOVIES_DATA, PERSONS_DATA, STUDIOS_DATA


# [AGC:START] tool=Cc author=fangkun


def ingest_movies_data() -> None:
    """导入电影、人物、制片厂数据到 Neo4j"""

    # 创建电影节点
    for movie in MOVIES_DATA:
        query = """
        MERGE (m:Movie {title: $title})
        ON CREATE SET
            m.released = $released,
            m.rating = $rating,
            m.tagline = $tagline,
            m.plot_summary = $plot_summary,
            m.genres = $genres,
            m.keywords = $keywords
        """
        Neo4jConnection.execute_write(query, movie.model_dump())

    # 创建人物节点
    for person in PERSONS_DATA:
        query = """
        MERGE (p:Person {name: $name})
        ON CREATE SET p.born = $born, p.gender = $gender
        """
        Neo4jConnection.execute_write(query, person.model_dump())

    # 创建制片厂节点
    for studio in STUDIOS_DATA:
        query = """
        MERGE (s:Studio {name: $name})
        ON CREATE SET s.country = $country
        """
        Neo4jConnection.execute_write(query, studio.model_dump())

    # 创建关系
    _create_relationships()


def _create_relationships() -> None:
    """创建电影相关关系"""
    relationships: List[tuple] = [
        # Inception
        ("Leonardo DiCaprio", "Inception", "ACTED_IN", {"roles": ["Cobb"]}),
        ("Michael Caine", "Inception", "ACTED_IN", {"roles": ["Miles"]}),
        ("Christopher Nolan", "Inception", "DIRECTED", {}),
        ("Christopher Nolan", "Inception", "WROTE", {}),
        ("Warner Bros.", "Inception", "DISTRIBUTED_BY", {"year": 2010}),

        # The Dark Knight
        ("Christian Bale", "The Dark Knight", "ACTED_IN", {"roles": ["Bruce Wayne"]}),
        ("Michael Caine", "The Dark Knight", "ACTED_IN", {"roles": ["Alfred"]}),
        ("Christopher Nolan", "The Dark Knight", "DIRECTED", {}),
        ("Christopher Nolan", "The Dark Knight", "WROTE", {}),
        ("Warner Bros.", "The Dark Knight", "DISTRIBUTED_BY", {"year": 2008}),
        ("Legendary Pictures", "The Dark Knight", "DISTRIBUTED_BY", {"year": 2008}),

        # Interstellar
        ("Matthew McConaughey", "Interstellar", "ACTED_IN", {"roles": ["Cooper"]}),
        ("Anne Hathaway", "Interstellar", "ACTED_IN", {"roles": ["Brand"]}),
        ("Michael Caine", "Interstellar", "ACTED_IN", {"roles": ["Professor Brand"]}),
        ("Christopher Nolan", "Interstellar", "DIRECTED", {}),
        ("Christopher Nolan", "Interstellar", "WROTE", {}),
        ("Warner Bros.", "Interstellar", "DISTRIBUTED_BY", {"year": 2014}),
        ("Paramount Pictures", "Interstellar", "DISTRIBUTED_BY", {"year": 2014}),
    ]

    for person_name, movie_title, rel_type, props in relationships:
        query = f"""
        MATCH (p {{name: $person_name}}), (m:Movie {{title: $movie_title}})
        MERGE (p)-[r:{rel_type}]->(m)
        SET r += $props
        """
        Neo4jConnection.execute_write(query, {
            "person_name": person_name,
            "movie_title": movie_title,
            "props": props
        })


# [AGC:END]
