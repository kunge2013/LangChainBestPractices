import bs4
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector

load_dotenv()

# 配置常量
VECTOR_INDEX_NAME = "news_vectors"
URLS = [
    "https://news.cctv.com/2026/07/31/ARTI2NyAaD4KVoKwvBvAUFXS260731.shtml?spm=C96370.PPDB2vhvSivD.ERPyWJCsPwT9.13",
    "https://news.cctv.com/2026/08/06/ARTINkpwMcE7v071bnBXl1WF260806.shtml?spm=C94212.P4YnMod9m2uD.ENPMkWvfnaiV.42",
    "https://news.cctv.com/2026/06/20/ARTIj8kI4cSTzWnwN0EXCv24260615.shtml?spm=C94212.PX2vlYqXvXQY.S57313.3",
]

def create_vector_store(force_recreate=False):
    """创建或加载向量库"""

    # 初始化嵌入模型
    embeddings = HuggingFaceEmbeddings(
        model_name="shibing624/text2vec-base-chinese",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    # 尝试加载已有的向量库
    if not force_recreate:
        try:
            db = Neo4jVector.from_existing_index(
                embedding=embeddings,
                url=os.environ.get("NEO4J_URI"),
                username=os.environ.get("NEO4J_USERNAME"),
                password=os.environ.get("NEO4J_PASSWORD"),
                database=os.environ.get("NEO4J_DATABASE"),
                index_name=VECTOR_INDEX_NAME,
                text_node_property="text",
                embedding_node_property="embedding"
            )
            print("✅ 成功加载已有向量库")
            return db
        except Exception as e:
            print(f"⚠️ 加载向量库失败: {e}")
            print("🔄 将重新创建向量库...")

    # 创建新的向量库
    print("📥 正在加载网页内容...")
    bs4_strainer = bs4.SoupStrainer()
    loader = WebBaseLoader(web_paths=URLS, bs_kwargs={"parse_only": bs4_strainer})
    docs = loader.load()

    print("✂️ 正在分割文本...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True
    )
    all_splits = text_splitter.split_documents(docs)
    print(f"📊 共分割为 {len(all_splits)} 个文本块")

    print("💾 正在创建向量库...")
    db = Neo4jVector.from_documents(
        documents=all_splits,
        embedding=embeddings,
        url=os.environ.get("NEO4J_URI"),
        username=os.environ.get("NEO4J_USERNAME"),
        password=os.environ.get("NEO4J_PASSWORD"),
        database=os.environ.get("NEO4J_DATABASE"),
        index_name=VECTOR_INDEX_NAME,
        text_node_property="text",
        embedding_node_property="embedding"
    )
    print("✅ 向量库创建完成")
    return db

def search_similarity(db, query, k=2):
    """执行相似度搜索"""
    print(f"\n🔍 查询: {query}")
    docs_with_score = db.similarity_search_with_score(query, k=k)

    print(f"📝 找到 {len(docs_with_score)} 个相关结果:")
    for i, (doc, score) in enumerate(docs_with_score, 1):
        print(f"\n--- 结果 {i} ---")
        print(f"相似度分数: {score:.4f}")
        print(f"内容预览: {doc.page_content[:200]}...")
        print(f"完整内容: {doc.page_content}")

def main():
    # 设置 force_recreate=False 来复用已有向量库
    # 设置为 True 强制重新创建
    db = create_vector_store(force_recreate=False)

    # 执行查询
    queries = [
        "煤电占比是多少",
        "外交部 广岛 核爆",
        "央视新闻 2026"
    ]

    for query in queries:
        search_similarity(db, query)

if __name__ == "__main__":
    main()