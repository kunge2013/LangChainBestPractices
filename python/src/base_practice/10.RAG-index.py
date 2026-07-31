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

load_dotenv()
page_url = "https://news.cctv.com/2026/07/31/ARTI2NyAaD4KVoKwvBvAUFXS260731.shtml?spm=C96370.PPDB2vhvSivD.ERPyWJCsPwT9.13"
bs4_strainer = bs4.SoupStrainer()

loader = WebBaseLoader(
    web_paths=(page_url,), bs_kwargs={"parse_only": bs4_strainer})

docs = loader.load()

print(len(docs))
print(type(docs[0]))
print(docs[0])

from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # char/
    chunk_overlap=200,
    add_start_index=True
)

all_splits = text_splitter.split_documents(docs)

print(len(all_splits))
print(all_splits[0])

from langchain_community.embeddings import DashScopeEmbeddings

embeddings = DashScopeEmbeddings(
    model=os.environ.get("EMBEDDING_MODEL", "text-embedding-v3"),
    dashscope_api_key=os.environ.get("EMBEDDING_API_KEY", "text-embedding-v3"),
)

from langchain_chroma import Chroma

vertor_store = Chroma(
    collection_name="rag_collection",
    embedding_function=embeddings,
    persist_directory="./rag_chrome_langchain_db"
)

ids = vertor_store.add_documents(documents=all_splits)
print(len(ids))