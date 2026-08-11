# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
向量索引构建模块
为电影的 plot_summary 字段生成 embedding 并创建 Neo4j 向量索引
"""
from data_init import Neo4jConnection
from config import settings
from langchain_community.embeddings import HuggingFaceEmbeddings


# [AGC:START] tool=Cc author=fangkun


def create_vector_index() -> None:
    """
    为 plot_summary 创建 Neo4j 向量索引

    使用 all-MiniLM-L6-v2 模型输出的 384 维向量，
    相似度函数使用 cosine。
    """
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


def update_movie_embeddings() -> None:
    """
    更新所有电影的 plot_summary embedding

    使用 HuggingFaceEmbeddings 加载 sentence-transformers/all-MiniLM-L6-v2 模型，
    对每部电影的 plot_summary 生成 embedding 并写入数据库。
    """
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


# [AGC:END]
