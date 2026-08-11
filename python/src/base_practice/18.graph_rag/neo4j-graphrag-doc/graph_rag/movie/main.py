# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
主入口：交互式电影问答系统
使用 OpenAI 协议，支持 dashscope 等兼容 API
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置模块会自动加载 python/.env
from config import settings
from langchain_openai import ChatOpenAI
from tools import create_graph_query_tool, create_vector_search_tool, create_recommender_tool
from agent import create_movie_agent


# [AGC:START] tool=Cc author=fangkun
def main():
    """主函数：交互式电影问答"""

    print("="*80)
    print("  电影 Graph RAG 问答系统")
    print("="*80)
    print(f"  LLM: {settings.llm.model_name} @ {settings.llm.base_url}")
    print(f"  Embedding: {settings.embedding.model_name} (device={settings.embedding.device})")
    print(f"  Neo4j: {settings.neo4j.uri}")
    print("="*80)

    # 初始化 LLM（使用 OpenAI 协议，支持 dashscope）
    llm = ChatOpenAI(
        model=settings.llm.model_name,
        temperature=settings.llm.temperature,
        openai_api_base=settings.llm.base_url,
        openai_api_key=settings.llm.api_key,
        max_retries=3,
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

            # 调用 Agent（LangGraph 格式）
            response = agent.invoke({"messages": [("user", question)]})

            print("\n" + "-"*80)
            print("回答:")
            # 从 messages 中提取最后的 AI 消息
            last_message = response["messages"][-1]
            print(last_message.content)
            print("-"*80)

        except KeyboardInterrupt:
            print("\n\n检测到 Ctrl+C，退出程序")
            break
        except Exception as e:
            print(f"\n[ERROR] 发生错误: {e}")
            import traceback
            traceback.print_exc()


# [AGC:END]


if __name__ == "__main__":
    main()
