## 索引
# 1.读取网页， Document，List[Document]
# 2.分割文本，文本段(chunk)，Document，List[Document]
# 3.向量化:文本段<=>向量， 需要嵌入模型来辅助
# 4.向量库:把多个文本段/向量存到向量库，OK了。
# pip install bs4
# 1.读取网页，按照页来管理，Document，List[Document]
from dotenv import load_dotenv
import os
from langchain_chroma import Chroma
from langchain.agents import create_agent
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool, ToolRuntime
import os

load_dotenv()

model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
    # qwen3.5-plus 默认开启 thinking 模式，该模式下不支持 tool_choice="required"/"any"
    # 而 create_agent 使用 response_format 时会设置 tool_choice="any" 来强制工具调用，
    # 因此需要关闭 thinking 模式
    extra_body={"enable_thinking": False},
)


from langchain_community.embeddings import DashScopeEmbeddings

embeddings = DashScopeEmbeddings(
    model=os.environ.get("EMBEDDING_MODEL", "text-embedding-v3"),
    dashscope_api_key=os.environ.get("EMBEDDING_API_KEY", "text-embedding-v3"),
)
# 向量
vertor_store = Chroma(
    collection_name="rag_collection",
    embedding_function=embeddings,
    persist_directory="./rag_chrome_langchain_db"
)

@tool(response_format="content_and_artifact")
def retrive_context(query:str):
    """检索信息，并作为答案 回答"""
    retrive_docs=vertor_store.similarity_search(query, k = 2)
    content = '\n\n'.join(
        (f"Source:{doc.metadata}\n , Content:{doc.page_content}") for doc in retrive_docs
    )
    return content, retrive_docs

sys_prompt = """
你是一个知识管理大师
你可以使用检索工具回答用户问题
"""

agent = create_agent(
    model=model,
    tools=[retrive_context],
    system_prompt=sys_prompt
)

results = agent.invoke(
    {"messages":[
        {
            "role":"user", "content":"我国电力煤电占比是多少？"
        }
    ]}
)

messages = results["messages"]
for msg in messages:
    msg.pretty_print()
