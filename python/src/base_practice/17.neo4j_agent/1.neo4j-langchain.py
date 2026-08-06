## 索引
# 1.读取网页， Document，List[Document]
# 2.分割文本，文本段(chunk)，Document，List[Document]
# 3.向量化:文本段<=>向量， 需要嵌入模型来辅助
# 4.向量库:把多个文本段/向量存到向量库，OK了。
# pip install bs4
# 1.读取网页，按照页来管理，Document，List[Document]

from langchain_community.document_loaders import WebBaseLoader
import bs4
from dotenv import load_dotenv
import os
from langchain_neo4j.vectorstores import neo4j_vector
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


load_dotenv()
page_url = "https://news.cctv.com/2026/07/31/ARTI2NyAaD4KVoKwvBvAUFXS260731.shtml?spm=C96370.PPDB2vhvSivD.ERPyWJCsPwT9.13"
bs4_strainer = bs4.SoupStrainer()

loader = WebBaseLoader(
    web_paths=(page_url,
               # 外交部谈广岛核爆81周年：日方应对历史心怀敬畏 不要再次走向被告席
               "https://news.cctv.com/2026/08/06/ARTINkpwMcE7v071bnBXl1WF260806.shtml?spm=C94212.P4YnMod9m2uD.ENPMkWvfnaiV.42",
               "https://news.cctv.com/2026/06/20/ARTIj8kI4cSTzWnwN0EXCv24260615.shtml?spm=C94212.PX2vlYqXvXQY.S57313.3",
               ), bs_kwargs={"parse_only": bs4_strainer})

docs = loader.load()



text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # char/
    chunk_overlap=200,
    add_start_index=True
)

all_splits = text_splitter.split_documents(docs)

embeddings = DashScopeEmbeddings(
    model=os.environ.get("EMBEDDING_MODEL", "text-embedding-v3"),
    dashscope_api_key=os.environ.get("EMBEDDING_API_KEY", "text-embedding-v3"),
)

db = neo4j_vector.Neo4jVector.from_documents(
    docs, embeddings,
    url=os.environ.get("NEO4J_URI"),
    username=os.environ.get("NEO4J_USERNAME"),
    password=os.environ.get("NEO4J_PASSWORD"),
    database=os.environ.get("NEO4J_DATABASE"),
)

query = "煤电占比是多少"
docs_with_score = db.similarity_search_with_score(query, k=2)

print(docs_with_score)