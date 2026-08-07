# Neo4j + HuggingFace Embedding + LangChain 接入知识库流程

## 一、整体架构

```
网页/文档 → 数据加载 → 文本分割 → 向量化 → Neo4j向量库 → 相似度检索
            (Loader)   (Splitter)  (Embedding)  (VectorStore)  (Search)
```

## 二、前置准备

### 2.1 环境依赖

```bash
pip install langchain langchain-community langchain-text-splitters langchain-huggingface langchain-neo4j bs4 python-dotenv
```

### 2.2 环境变量配置

在项目根目录创建 `.env` 文件，配置以下变量：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

> 如使用 HuggingFace 在线嵌入模型，需确保网络可访问或配置本地模型路径。

### 2.3 Neo4j 实例

- 本地部署或使用 Neo4j Aura 云服务
- 确保 Neo4j 实例已启动且可连接
- 无需预先创建索引，代码会自动处理

## 三、接入步骤

### 步骤 1：初始化嵌入模型

使用 HuggingFace 的 `text2vec-base-chinese` 中文嵌入模型：

```python
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="shibing624/text2vec-base-chinese",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)
```

**关键参数说明：**

| 参数 | 说明 |
|------|------|
| `model_name` | 嵌入模型名称，支持 HuggingFace Hub 或本地路径 |
| `model_kwargs.device` | 推理设备，`cpu` 或 `cuda` |
| `encode_kwargs.normalize_embeddings` | 是否归一化向量，推荐设为 `True` |

### 步骤 2：加载文档数据

从网页加载原始文档：

```python
from langchain_community.document_loaders import WebBaseLoader
import bs4

bs4_strainer = bs4.SoupStrainer()
loader = WebBaseLoader(
    web_paths=URLS,
    bs_kwargs={"parse_only": bs4_strainer}
)
docs = loader.load()
```

> `bs4.SoupStrainer()` 用于加速解析，只提取核心内容。也可使用其他 Loader（如 `DirectoryLoader` 加载本地文件）。

### 步骤 3：文本分割

将长文档切分为固定大小的 chunk：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    add_start_index=True
)
all_splits = text_splitter.split_documents(docs)
```

**关键参数说明：**

| 参数 | 说明 |
|------|------|
| `chunk_size` | 每个文本块的最大字符数 |
| `chunk_overlap` | 相邻块的重叠字符数，避免信息断裂 |
| `add_start_index` | 是否记录块在原文中的起始位置 |

### 步骤 4：创建 Neo4j 向量库

将分割后的文本块向量化并存入 Neo4j：

```python
from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector

db = Neo4jVector.from_documents(
    documents=all_splits,
    embedding=embeddings,
    url=os.environ.get("NEO4J_URI"),
    username=os.environ.get("NEO4J_USERNAME"),
    password=os.environ.get("NEO4J_PASSWORD"),
    database=os.environ.get("NEO4J_DATABASE"),
    index_name="news_vectors",
    text_node_property="text",
    embedding_node_property="embedding"
)
```

**Neo4j 中生成的数据结构：**

- 每个 chunk 存储为 Neo4j 节点
- 节点属性：`text`（文本内容）、`metadata`（来源、索引等）
- 节点属性：`embedding`（向量表示）
- 自动创建向量索引 `news_vectors`

### 步骤 5：复用已有向量库

避免每次都重新加载和向量化：

```python
db = Neo4jVector.from_existing_index(
    embedding=embeddings,
    url=os.environ.get("NEO4J_URI"),
    username=os.environ.get("NEO4J_USERNAME"),
    password=os.environ.get("NEO4J_PASSWORD"),
    database=os.environ.get("NEO4J_DATABASE"),
    index_name="news_vectors",
    text_node_property="text",
    embedding_node_property="embedding"
)
```

**设计模式：** 首次创建 → 后续复用，通过 `force_recreate` 标志控制：

```python
def create_vector_store(force_recreate=False):
    if not force_recreate:
        try:
            return Neo4jVector.from_existing_index(...)  # 复用
        except Exception:
            pass  # 不存在则走创建流程
    return Neo4jVector.from_documents(...)  # 首次创建
```

### 步骤 6：相似度检索

```python
docs_with_score = db.similarity_search_with_score(query, k=2)

for doc, score in docs_with_score:
    print(f"相似度分数: {score:.4f}")
    print(f"内容: {doc.page_content}")
```

**返回值说明：**

- 返回 `(Document, score)` 元组列表
- `score` 越接近 1 表示越相似（归一化后的余弦相似度）
- `k` 控制返回结果数量

## 四、完整流程概览

```
┌──────────────────────────────────────────────────────────────┐
│                     create_vector_store()                     │
│                                                               │
│  force_recreate=False? ──是──> from_existing_index() ──> db  │
│         │                                                    │
│        否                                                    │
│         ▼                                                    │
│  WebBaseLoader.load() ──> docs                               │
│         ▼                                                    │
│  RecursiveCharacterTextSplitter.split_documents() ──> chunks │
│         ▼                                                    │
│  Neo4jVector.from_documents() ──> db                         │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    search_similarity(db, query)               │
│                                                               │
│  db.similarity_search_with_score(query, k=2)                 │
│  ──> [(doc, score), ...]                                     │
└──────────────────────────────────────────────────────────────┘
```

## 五、关键依赖版本

| 包名 | 用途 |
|------|------|
| `langchain-huggingface` | HuggingFace 嵌入模型集成 |
| `langchain-neo4j` | Neo4j 向量存储后端 |
| `langchain-text-splitters` | 文本分割工具 |
| `langchain-community` | 社区 Loader（WebBaseLoader 等） |
| `bs4` | HTML 解析加速 |
| `python-dotenv` | 环境变量加载 |

## 六、扩展方向

1. **数据源扩展**：除网页外，支持 PDF、Word、Markdown 等本地文件加载
2. **混合检索**：结合 BM25 关键词检索 + 向量相似度检索
3. **RAG 链路**：对接 LLM（如 OpenAI、通义千问），实现检索增强生成问答
4. **知识图谱**：利用 Neo4j 图数据库特性，构建实体关系图谱 + 向量检索的组合查询
5. **增量更新**：检测文档变更，仅对新增/修改的 chunk 进行向量化更新
