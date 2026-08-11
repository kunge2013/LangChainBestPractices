# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
混合推荐工具
结合图结构查询（GraphQueryTool）和向量语义检索（VectorSearchTool）实现混合推荐
"""
from langchain_core.tools import Tool
from langchain_core.language_models import BaseLLM
from .graph_query_tool import create_graph_query_tool
from .vector_search_tool import create_vector_search_tool


# [AGC:START] tool=Cc author=fangkun


def create_recommender_tool(llm: BaseLLM, embedding_llm: BaseLLM) -> Tool:
    """创建混合推荐工具

    组合图查询工具（获取结构化电影信息）和向量搜索工具（语义相似度匹配），
    在查询中同时利用图结构和向量语义两路结果进行融合推荐。

    Args:
        llm: 用于图查询的大语言模型
        embedding_llm: 用于向量搜索的嵌入模型

    Returns:
        Tool: 混合推荐工具实例
    """

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


# [AGC:END]
