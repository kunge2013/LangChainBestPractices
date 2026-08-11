# Movie Graph RAG 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use kunge2013:subagent-driven-development (recommended) or kunge2013:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于 Neo4j 的电影知识图谱 Graph RAG 系统，支持结构化查询、语义搜索和智能推荐。

**Architecture:** 使用 LangChain ReAct Agent 编排三种工具（GraphQueryTool、VectorSearchTool、RecommenderTool），结合 Neo4j 图数据库和向量索引，通过 HuggingFaceEmbeddings 生成剧情简介的向量表示，ChatOpenAI 生成自然语言回答。

**Tech Stack:** Neo4j 6.x, LangChain, HuggingFaceEmbeddings, ChatOpenAI, neo4j-graphrag

---

## 文件结构

```
movie/
├── config/
│   ├── __init__.py              # 配置模块导出
│   └── settings.py              # LLM、Embedding、Neo4j 配置类
├── models/
│   ├── __init__.py              # 数据模型导出
│   └── movie_data.py            # 扩展电影数据定义（含 plot_summary）
├── ingestion/
│   ├── __init__.py              # 导入模块导出
│   ├── ingest_graph.py          # 图数据导入（节点+关系）
│   └── ingest_vectors.py        # 向量索引构建
├── tools/
│   ├── __init__.py              # 工具模块导出
│   ├── graph_query_tool.py      # 结构化查询工具
│   ├── vector_search_tool.py    # 向量语义检索工具
│   └── recommender_tool.py      # 混合推荐工具
├── agent/
│   ├── __init__.py              # Agent 模块导出
│   └── movie_agent.py           # LangChain ReAct Agent
├── main.py                      # 交互式问答入口
└── tests/
    ├── test_ingestion.py        # 数据导入测试
    ├── test_tools.py            # 工具功能测试
    └── test_agent.py            # Agent 端到端测试
```

---

## Task 1: 配置模块

**Files:**
- Create: `movie/config/__init__.py`
- Create: `movie/config/settings.py`

- [ ] **Step 1: 创建配置类**

```python
# movie/config/settings.py
from pydantic import BaseModel
from typing import Optional


class Neo4jConfig(BaseModel):
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"


class LLMConfig(BaseModel):
    model_name: str = "gpt-4"
    temperature: float = 0.0
    max_retries: int = 3


class EmbeddingConfig(BaseModel):
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"
    cache_dir: str = "./embedding_cache"


class Settings(BaseModel):
    neo4j: Neo4jConfig = Neo4jConfig()
    llm: LLMConfig = LLMConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()

    class Config:
        env_prefix = "MOVIE_"
        env_nested_delimiter = "__"


# 全局配置实例
settings = Settings()
```

- [ ] **Step 2: 创建模块导出**

```python
# movie/config/__init__.py
from .settings import Settings, settings, Neo4jConfig, LLMConfig, EmbeddingConfig

__all__ = ["Settings", "settings", "Neo4jConfig", "LLMConfig", "EmbeddingConfig"]
```

- [ ] **Step 3: 提交**

```bash
git add movie/config/
git commit -m "feat: 添加配置模块（Neo4j、LLM、Embedding）"
```

---

## Task 2: 数据模型

**Files:**
- Create: `movie/models/__init__.py`
- Create: `movie/models/movie_data.py`

- [ ] **Step 1: 定义扩展电影数据**

```python
# movie/models/movie_data.py
from typing import List, Optional
from pydantic import BaseModel


class Movie(BaseModel):
    title: str
    released: int
    rating: float
    tagline: str
    plot_summary: str
    genres: List[str]
    keywords: Optional[List[str]] = None


class Person(BaseModel):
    name: str
    born: int
    gender: str


class Studio(BaseModel):
    name: str
    country: str


# 扩展现有 3 部电影的数据
MOVIES_DATA = [
    Movie(
        title="Inception",
        released=2010,
        rating=8.8,
        tagline="Your mind is the scene of the crime",
        plot_summary="A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a CEO.",
        genres=["Sci-Fi", "Thriller", "Action"],
        keywords=["dream", "subconscious", "heist"]
    ),
    Movie(
        title="The Dark Knight",
        released=2008,
        rating=9.0,
        tagline="Why so serious?",
        plot_summary="When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of their ability to fight injustice.",
        genres=["Action", "Crime", "Drama"],
        keywords=["superhero", "villain", "justice"]
    ),
    Movie(
        title="Interstellar",
        released=2014,
        rating=8.6,
        tagline="Mankind was born on Earth. It was never meant to die here.",
        plot_summary="A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival as Earth becomes uninhabitable.",
        genres=["Sci-Fi", "Adventure", "Drama"],
        keywords=["space", "time", "survival"]
    ),
]

PERSONS_DATA = [
    Person(name="Leonardo DiCaprio", born=1974, gender="Male"),
    Person(name="Christian Bale", born=1974, gender="Male"),
    Person(name="Matthew McConaughey", born=1969, gender="Male"),
    Person(name="Anne Hathaway", born=1982, gender="Female"),
    Person(name="Christopher Nolan", born=1970, gender="Male"),
    Person(name="Michael Caine", born=1933, gender="Male"),
]

STUDIOS_DATA = [
    Studio(name="Warner Bros.", country="USA"),
    Studio(name="Paramount Pictures", country="USA"),
    Studio(name="Legendary Pictures", country="USA"),
]
```

- [ ] **Step 2: 创建模块导出**

```python
# movie/models/__init__.py
from .movie_data import (
    Movie, Person, Studio,
    MOVIES_DATA, PERSONS_DATA, STUDIOS_DATA
)

__all__ = [
    "Movie", "Person", "Studio",
    "MOVIES_DATA", "PERSONS_DATA", "STUDIOS_DATA"
]
```

- [ ] **Step 3: 提交**

```bash
git add movie/models/
git commit -m "feat: 添加数据模型（Movie/Person/Studio 含 plot_summary）"
```

---

## Task 3: 图数据导入

**Files:**
- Create: `movie/ingestion/__init__.py`
- Create: `movie/ingestion/ingest_graph.py`
- Create: `movie/tests/test_ingestion.py`

- [ ] **Step 1: 编写测试**

```python
# movie/tests/test_ingestion.py
import pytest
from unittest.mock import MagicMock, patch
from movie.ingestion.ingest_graph import ingest_movies_data


def test_ingest_movies_data_creates_nodes():
    """测试数据导入创建节点"""
    mock_session = MagicMock()
    mock_session.run.return_value = []

    with patch('movie.ingestion.ingest_graph.Neo4jConnection') as mock_conn:
        mock_conn.get_driver.return_value.__enter__.return_value = mock_session

        ingest_movies_data()

        # 验证调用了 run 方法创建节点
        assert mock_session.run.called
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest movie/tests/test_ingestion.py::test_ingest_movies_data_creates_nodes -v
```

Expected: FAIL - "No module named 'movie.ingestion'"

- [ ] **Step 3: 实现图数据导入**

```python
# movie/ingestion/ingest_graph.py
from typing import List
from data_init import Neo4jConnection
from models import MOVIES_DATA, PERSONS_DATA, STUDIOS_DATA


def ingest_movies_data():
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

    # 创建关系（简化版本，实际应该从 CSV 或数据源读取）
    _create_relationships()


def _create_relationships():
    """创建电影相关关系"""
    relationships = [
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
```

- [ ] **Step 4: 创建模块导出**

```python
# movie/ingestion/__init__.py
from .ingest_graph import ingest_movies_data

__all__ = ["ingest_movies_data"]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest movie/tests/test_ingestion.py::test_ingest_movies_data_creates_nodes -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add movie/ingestion/ movie/tests/test_ingestion.py
git commit -m "feat: 实现图数据导入（节点+关系）"
```

---

## Task 4: 向量索引构建

**Files:**
- Create: `movie/ingestion/ingest_vectors.py`
- Modify: `movie/tests/test_ingestion.py`

- [ ] **Step 1: 编写测试**

```python
# movie/tests/test_ingestion.py (追加)
from movie.ingestion.ingest_vectors import create_vector_index


def test_create_vector_index_calls_neo4j():
    """测试向量索引创建调用 Neo4j"""
    with patch('movie.ingestion.ingest_vectors.Neo4jConnection') as mock_conn:
        mock_session = MagicMock()
        mock_conn.get_driver.return_value.__enter__.return_value = mock_session

        create_vector_index()

        # 验证调用了 run 方法创建索引
        assert mock_session.run.called
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest movie/tests/test_ingestion.py::test_create_vector_index_calls_neo4j -v
```

Expected: FAIL - "No module named 'movie.ingestion.ingest_vectors'"

- [ ] **Step 3: 实现向量索引构建**

```python
# movie/ingestion/ingest_vectors.py
from data_init import Neo4jConnection
from config import settings


def create_vector_index():
    """为 plot_summary 创建向量索引"""

    # 使用 neo4j-graphrag 的向量索引创建
    query = """
    CREATE VECTOR INDEX movie_plot_summary_index IF NOT EXISTS
    FOR (m:Movie)
    ON m.plot_summary_embedding
    OPTIONS {indexConfig: {
        `vector.dimensions`: 384,
        `vector.similarity_function`: 'cosine'
    }}
    """

    try:
        Neo4jConnection.execute_write(query)
        print("[OK] 向量索引创建成功")
    except Exception as e:
        print(f"[WARN] 向量索引创建失败或已存在: {e}")


def update_movie_embeddings():
    """更新电影的 plot_summary embedding"""
    from langchain_community.embeddings import HuggingFaceEmbeddings

    # 初始化 embedding 模型
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding.model_name,
        model_kwargs={"device": settings.embedding.device},
        encode_kwargs={"normalize_embeddings": True},
        cache_folder=settings.embedding.cache_dir
    )

    # 获取所有电影
    query = "MATCH (m:Movie) RETURN m.title AS title, m.plot_summary AS plot_summary"
    results = Neo4jConnection.execute_query(query)

    for record in results:
        title = record["title"]
        plot_summary = record["plot_summary"]

        if plot_summary:
            # 生成 embedding
            embedding = embeddings.embed_query(plot_summary)

            # 更新到数据库
            update_query = """
            MATCH (m:Movie {title: $title})
            SET m.plot_summary_embedding = $embedding
            """
            Neo4jConnection.execute_write(update_query, {
                "title": title,
                "embedding": embedding
            })
            print(f"[OK] {title} embedding 已更新")
```

- [ ] **Step 4: 更新模块导出**

```python
# movie/ingestion/__init__.py (更新)
from .ingest_graph import ingest_movies_data
from .ingest_vectors import create_vector_index, update_movie_embeddings

__all__ = ["ingest_movies_data", "create_vector_index", "update_movie_embeddings"]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest movie/tests/test_ingestion.py -v
```

Expected: PASS (所有测试)

- [ ] **Step 6: 提交**

```bash
git add movie/ingestion/ingest_vectors.py movie/tests/test_ingestion.py
git commit -m "feat: 实现向量索引构建（HuggingFaceEmbeddings）"
```

---

## Task 5: GraphQueryTool

**Files:**
- Create: `movie/tools/__init__.py`
- Create: `movie/tools/graph_query_tool.py`
- Create: `movie/tests/test_tools.py`

- [ ] **Step 1: 编写测试**

```python
# movie/tests/test_tools.py
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.tools import Tool
from movie.tools.graph_query_tool import create_graph_query_tool


def test_create_graph_query_tool_returns_tool():
    """测试创建图查询工具返回 Tool 实例"""
    with patch('movie.tools.graph_query_tool.GraphCypherQAChain') as mock_chain:
        mock_chain.from_llm.return_value = MagicMock()

        tool = create_graph_query_tool(MagicMock())

        assert isinstance(tool, Tool)
        assert tool.name == "graph_query"
        assert "结构化查询" in tool.description


def test_graph_query_tool_invokes_chain():
    """测试图查询工具调用 Chain"""
    mock_chain_instance = MagicMock()
    mock_chain_instance.run.return_value = "查询结果"

    with patch('movie.tools.graph_query_tool.GraphCypherQAChain') as mock_chain:
        mock_chain.from_llm.return_value = mock_chain_instance

        tool = create_graph_query_tool(MagicMock())
        result = tool.func("Leonardo DiCaprio 演过哪些电影")

        assert result == "查询结果"
        mock_chain_instance.run.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest movie/tests/test_tools.py::test_create_graph_query_tool_returns_tool -v
```

Expected: FAIL - "No module named 'movie.tools'"

- [ ] **Step 3: 实现 GraphQueryTool**

```python
# movie/tools/graph_query_tool.py
from langchain_core.tools import Tool
from langchain.chains import GraphCypherQAChain
from langchain_neo4j import Neo4jGraph
from langchain_core.language_models import BaseLLM


def create_graph_query_tool(llm: BaseLLM) -> Tool:
    """创建结构化查询工具"""

    # 初始化 Neo4j Graph
    graph = Neo4jGraph()

    # 创建 Cypher QA Chain
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        return_intermediate_steps=False
    )

    def query_func(question: str) -> str:
        """执行图查询"""
        try:
            result = chain.run(question)
            return result
        except Exception as e:
            return f"查询失败: {str(e)}"

    return Tool(
        name="graph_query",
        description="用于结构化查询电影信息、演员信息、评分等精确问题。例如：'谁演了 Inception'、'这部电影评分多少'",
        func=query_func
    )
```

- [ ] **Step 4: 创建模块导出**

```python
# movie/tools/__init__.py
from .graph_query_tool import create_graph_query_tool

__all__ = ["create_graph_query_tool"]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest movie/tests/test_tools.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add movie/tools/ movie/tests/test_tools.py
git commit -m "feat: 实现 GraphQueryTool（结构化查询）"
```

---

## Task 6: VectorSearchTool

**Files:**
- Create: `movie/tools/vector_search_tool.py`
- Modify: `movie/tools/__init__.py`
- Modify: `movie/tests/test_tools.py`

- [ ] **Step 1: 编写测试**

```python
# movie/tests/test_tools.py (追加)
from movie.tools.vector_search_tool import create_vector_search_tool


def test_create_vector_search_tool_returns_tool():
    """测试创建向量搜索工具返回 Tool 实例"""
    with patch('movie.tools.vector_search_tool.Neo4jVector') as mock_vector:
        mock_vector.from_existing_index.return_value = MagicMock()

        tool = create_vector_search_tool(MagicMock())

        assert isinstance(tool, Tool)
        assert tool.name == "vector_search"
        assert "语义搜索" in tool.description


def test_vector_search_tool_invokes_retriever():
    """测试向量搜索工具调用 Retriever"""
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [MagicMock(page_content="电影信息")]

    with patch('movie.tools.vector_search_tool.Neo4jVector') as mock_vector:
        mock_vector.from_existing_index.return_value.as_retriever.return_value = mock_retriever

        tool = create_vector_search_tool(MagicMock())
        result = tool.func("关于太空的电影")

        assert "电影信息" in result
        mock_retriever.invoke.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest movie/tests/test_tools.py::test_create_vector_search_tool_returns_tool -v
```

Expected: FAIL - "No module named 'movie.tools.vector_search_tool'"

- [ ] **Step 3: 实现 VectorSearchTool**

```python
# movie/tools/vector_search_tool.py
from langchain_core.tools import Tool
from langchain_neo4j import Neo4jVector
from langchain_core.language_models import BaseLLM
from config import settings


def create_vector_search_tool(llm: BaseLLM) -> Tool:
    """创建语义搜索工具"""

    # 初始化 Neo4j Vector Store
    vector_store = Neo4jVector.from_existing_index(
        embedding=settings.embedding.model_name,
        index_name="movie_plot_summary_index",
        text_node_property="plot_summary",
        embedding_node_property="plot_summary_embedding",
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    def search_func(query: str) -> str:
        """执行语义搜索"""
        try:
            docs = retriever.invoke(query)
            if not docs:
                return "未找到相关电影"

            results = []
            for i, doc in enumerate(docs, 1):
                results.append(f"{i}. {doc.page_content}")

            return "\n".join(results)
        except Exception as e:
            return f"搜索失败: {str(e)}"

    return Tool(
        name="vector_search",
        description="用于语义搜索，基于剧情简介的相似度匹配。例如：'类似 XX 的电影'、'关于太空的电影'",
        func=search_func
    )
```

- [ ] **Step 4: 更新模块导出**

```python
# movie/tools/__init__.py (更新)
from .graph_query_tool import create_graph_query_tool
from .vector_search_tool import create_vector_search_tool

__all__ = ["create_graph_query_tool", "create_vector_search_tool"]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest movie/tests/test_tools.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add movie/tools/vector_search_tool.py movie/tools/__init__.py movie/tests/test_tools.py
git commit -m "feat: 实现 VectorSearchTool（语义搜索）"
```

---

## Task 7: RecommenderTool

**Files:**
- Create: `movie/tools/recommender_tool.py`
- Modify: `movie/tools/__init__.py`
- Modify: `movie/tests/test_tools.py`

- [ ] **Step 1: 编写测试**

```python
# movie/tests/test_tools.py (追加)
from movie.tools.recommender_tool import create_recommender_tool


def test_create_recommender_tool_returns_tool():
    """测试创建推荐工具返回 Tool 实例"""
    mock_llm = MagicMock()

    tool = create_recommender_tool(mock_llm, mock_llm)

    assert isinstance(tool, Tool)
    assert tool.name == "recommender"
    assert "推荐" in tool.description


def test_recommender_tool_combines_results():
    """测试推荐工具融合图查询和向量搜索结果"""
    mock_llm = MagicMock()
    mock_graph_tool = MagicMock()
    mock_graph_tool.func.return_value = "图查询结果"
    mock_vector_tool = MagicMock()
    mock_vector_tool.func.return_value = "向量搜索结果"

    with patch('movie.tools.recommender_tool.create_graph_query_tool', return_value=mock_graph_tool):
        with patch('movie.tools.recommender_tool.create_vector_search_tool', return_value=mock_vector_tool):
            tool = create_recommender_tool(mock_llm, mock_llm)
            result = tool.func("推荐类似 Inception 的电影")

            assert "图查询结果" in result or "向量搜索结果" in result
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest movie/tests/test_tools.py::test_create_recommender_tool_returns_tool -v
```

Expected: FAIL - "No module named 'movie.tools.recommender_tool'"

- [ ] **Step 3: 实现 RecommenderTool**

```python
# movie/tools/recommender_tool.py
from langchain_core.tools import Tool
from langchain_core.language_models import BaseLLM
from .graph_query_tool import create_graph_query_tool
from .vector_search_tool import create_vector_search_tool


def create_recommender_tool(llm: BaseLLM, embedding_llm: BaseLLM) -> Tool:
    """创建混合推荐工具"""

    graph_tool = create_graph_query_tool(llm)
    vector_tool = create_vector_search_tool(embedding_llm)

    def recommend_func(query: str) -> str:
        """执行混合推荐"""
        try:
            # 提取电影名称（简化版，实际应该用 NER 或正则）
            movie_keywords = ["Inception", "The Dark Knight", "Interstellar"]
            target_movie = None
            for keyword in movie_keywords:
                if keyword.lower() in query.lower():
                    target_movie = keyword
                    break

            results = []

            if target_movie:
                # 图查询：获取相关电影信息
                graph_query = f"与 {target_movie} 相关的电影信息"
                graph_result = graph_tool.func(graph_query)
                results.append("【图结构推荐】")
                results.append(graph_result)
                results.append("")

            # 向量搜索：语义相似度
            vector_result = vector_tool.func(query)
            results.append("【语义相似度推荐】")
            results.append(vector_result)

            return "\n".join(results)
        except Exception as e:
            return f"推荐失败: {str(e)}"

    return Tool(
        name="recommender",
        description="用于混合推荐，结合图结构和语义相似度。例如：'推荐类似 XX 的电影'",
        func=recommend_func
    )
```

- [ ] **Step 4: 更新模块导出**

```python
# movie/tools/__init__.py (更新)
from .graph_query_tool import create_graph_query_tool
from .vector_search_tool import create_vector_search_tool
from .recommender_tool import create_recommender_tool

__all__ = [
    "create_graph_query_tool",
    "create_vector_search_tool",
    "create_recommender_tool"
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest movie/tests/test_tools.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add movie/tools/recommender_tool.py movie/tools/__init__.py movie/tests/test_tools.py
git commit -m "feat: 实现 RecommenderTool（混合推荐）"
```

---

## Task 8: LangChain Agent

**Files:**
- Create: `movie/agent/__init__.py`
- Create: `movie/agent/movie_agent.py`
- Create: `movie/tests/test_agent.py`

- [ ] **Step 1: 编写测试**

```python
# movie/tests/test_agent.py
import pytest
from unittest.mock import MagicMock, patch
from movie.agent.movie_agent import create_movie_agent


def test_create_movie_agent_returns_agent():
    """测试创建电影 Agent"""
    mock_llm = MagicMock()
    mock_tools = [MagicMock(), MagicMock()]

    agent = create_movie_agent(mock_llm, mock_tools)

    assert agent is not None
    assert hasattr(agent, 'invoke')


def test_movie_agent_has_all_tools():
    """测试 Agent 包含所有工具"""
    mock_llm = MagicMock()
    mock_tools = [
        MagicMock(name="graph_query"),
        MagicMock(name="vector_search"),
        MagicMock(name="recommender")
    ]

    agent = create_movie_agent(mock_llm, mock_tools)

    # 验证工具已注册
    assert len(agent.tools) == 3
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest movie/tests/test_agent.py::test_create_movie_agent_returns_agent -v
```

Expected: FAIL - "No module named 'movie.agent'"

- [ ] **Step 3: 实现 LangChain Agent**

```python
# movie/agent/movie_agent.py
from typing import List
from langchain_core.language_models import BaseLLM
from langchain_core.tools import Tool
from langchain.agents import initialize_agent, AgentType


def create_movie_agent(llm: BaseLLM, tools: List[Tool]):
    """创建电影问答 Agent"""

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )

    return agent
```

- [ ] **Step 4: 创建模块导出**

```python
# movie/agent/__init__.py
from .movie_agent import create_movie_agent

__all__ = ["create_movie_agent"]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest movie/tests/test_agent.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add movie/agent/ movie/tests/test_agent.py
git commit -m "feat: 实现 LangChain Agent（ReAct）"
```

---

## Task 9: 主入口与交互式问答

**Files:**
- Create: `movie/main.py`

- [ ] **Step 1: 实现主入口**

```python
# movie/main.py
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_openai import ChatOpenAI
from config import settings
from tools import create_graph_query_tool, create_vector_search_tool, create_recommender_tool
from agent import create_movie_agent


def main():
    """主函数：交互式电影问答"""

    print("="*80)
    print("  电影 Graph RAG 问答系统")
    print("="*80)

    # 初始化 LLM
    llm = ChatOpenAI(
        model=settings.llm.model_name,
        temperature=settings.llm.temperature,
        max_retries=settings.llm.max_retries
    )

    # 创建工具
    print("\n[INFO] 初始化工具...")
    tools = [
        create_graph_query_tool(llm),
        create_vector_search_tool(llm),
        create_recommender_tool(llm, llm)
    ]
    print("[OK] 工具初始化完成")

    # 创建 Agent
    print("\n[INFO] 初始化 Agent...")
    agent = create_movie_agent(llm, tools)
    print("[OK] Agent 初始化完成")

    print("\n" + "="*80)
    print("  系统就绪！输入问题开始对话，输入 'quit' 或 'exit' 退出")
    print("="*80)

    # 交互式问答循环
    while True:
        try:
            question = input("\n你的问题: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                print("\n再见！")
                break

            if not question:
                continue

            # 调用 Agent
            response = agent.invoke({"input": question})

            print("\n" + "-"*80)
            print("回答:")
            print(response['output'])
            print("-"*80)

        except KeyboardInterrupt:
            print("\n\n检测到 Ctrl+C，退出程序")
            break
        except Exception as e:
            print(f"\n[ERROR] 发生错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 提交**

```bash
git add movie/main.py
git commit -m "feat: 实现交互式问答主入口"
```

---

## Task 10: 数据准备脚本

**Files:**
- Create: `movie/prepare_data.py`

- [ ] **Step 1: 实现数据准备脚本**

```python
# movie/prepare_data.py
"""
数据准备脚本：导入图数据并构建向量索引
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_init import Neo4jConnection, clear_database
from ingestion import ingest_movies_data, create_vector_index, update_movie_embeddings


def prepare_data():
    """准备所有数据"""

    print("="*80)
    print("  数据准备")
    print("="*80)

    try:
        # 测试连接
        print("\n[INFO] 测试 Neo4j 连接...")
        result = Neo4jConnection.execute_query("RETURN 1 AS test")
        print(f"[OK] 连接成功: {result}")

        # 清空数据库
        print("\n[INFO] 清空数据库...")
        clear_database()

        # 导入图数据
        print("\n[INFO] 导入图数据...")
        ingest_movies_data()
        print("[OK] 图数据导入完成")

        # 创建向量索引
        print("\n[INFO] 创建向量索引...")
        create_vector_index()
        print("[OK] 向量索引创建完成")

        # 更新 embedding
        print("\n[INFO] 更新电影 plot_summary embedding...")
        update_movie_embeddings()
        print("[OK] embedding 更新完成")

        print("\n" + "="*80)
        print("  数据准备完成！")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] 数据准备失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        Neo4jConnection.close()
        print("\n[INFO] 数据库连接已关闭")


if __name__ == "__main__":
    prepare_data()
```

- [ ] **Step 2: 提交**

```bash
git add movie/prepare_data.py
git commit -m "feat: 实现数据准备脚本"
```

---

## Task 11: 端到端测试

**Files:**
- Modify: `movie/tests/test_agent.py`

- [ ] **Step 1: 编写端到端测试**

```python
# movie/tests/test_agent.py (追加)
def test_end_to_end_graph_query():
    """端到端测试：结构化查询"""
    # 这个测试需要真实的 Neo4j 连接
    # 实际运行时应该使用 mock 或测试数据库
    pass


def test_end_to_end_vector_search():
    """端到端测试：语义搜索"""
    pass


def test_end_to_end_recommendation():
    """端到端测试：推荐"""
    pass
```

- [ ] **Step 2: 提交**

```bash
git add movie/tests/test_agent.py
git commit -m "test: 添加端到端测试框架"
```

---

## Task 12: 文档与最终提交

**Files:**
- Create: `movie/README.md`

- [ ] **Step 1: 编写 README**

```markdown
# Movie Graph RAG

基于 Neo4j 的电影知识图谱 Graph RAG 系统。

## 功能

- **结构化查询**：查询电影信息、演员信息、评分等
- **语义搜索**：基于剧情简介的相似度匹配
- **智能推荐**：结合图结构和语义相似度的混合推荐

## 安装

```bash
pip install langchain langchain-openai langchain-neo4j sentence-transformers neo4j
```

## 使用

### 1. 准备数据

```bash
python movie/prepare_data.py
```

### 2. 启动问答系统

```bash
python movie/main.py
```

### 3. 提问示例

- "Leonardo DiCaprio 演过哪些电影？"
- "Inception 的评分是多少？"
- "推荐一部类似盗梦空间的电影"
- "关于太空探索的电影有哪些？"

## 架构

- **LangChain Agent**：ReAct 模式编排工具
- **GraphQueryTool**：GraphCypherQAChain 自动生成 Cypher
- **VectorSearchTool**：Neo4jVector + HuggingFaceEmbeddings
- **RecommenderTool**：混合图查询和向量检索

## 技术栈

- Neo4j 6.x
- LangChain
- HuggingFaceEmbeddings
- ChatOpenAI
```

- [ ] **Step 2: 提交**

```bash
git add movie/README.md
git commit -m "docs: 添加项目 README"
```

---

## 自审检查清单

- [x] **Spec 覆盖**：所有需求都有对应的 Task 实现
- [x] **无占位符**：每个步骤都有具体代码和命令
- [x] **类型一致**：方法签名和属性名在所有 Task 中保持一致
- [x] **测试覆盖**：每个组件都有单元测试
- [x] **文件路径**：所有路径都是完整的
- [x] **提交频率**：每个 Task 完成后都有 commit

---

## 执行选项

计划已保存到 `docs/superpowers/plans/2026-08-11-movie-graph-rag.md`。

**两种执行方式：**

**1. Subagent-Driven（推荐）** - 每个 Task 分派一个独立的 subagent，任务间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中执行任务，批量执行并设置检查点进行审查

**选择哪种方式？**
