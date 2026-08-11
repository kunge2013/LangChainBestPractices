# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
工具的单元测试
验证 GraphQueryTool 和 VectorSearchTool 的创建和调用逻辑
"""
import pytest
from unittest.mock import MagicMock, patch


# [AGC:START] tool=Cc author=fangkun


def test_create_graph_query_tool_returns_tool():
    """测试创建图查询工具返回 Tool 实例"""
    with patch('tools.graph_query_tool.GraphCypherQAChain') as mock_chain:
        with patch('tools.graph_query_tool.Neo4jGraph'):
            mock_chain.from_llm.return_value = MagicMock()

            from tools.graph_query_tool import create_graph_query_tool
            tool = create_graph_query_tool(MagicMock())

            assert tool is not None
            assert tool.name == "graph_query"
            assert "结构化查询" in tool.description


def test_graph_query_tool_invokes_chain():
    """测试图查询工具调用 Chain"""
    mock_chain_instance = MagicMock()
    mock_chain_instance.run.return_value = "查询结果"

    with patch('tools.graph_query_tool.GraphCypherQAChain') as mock_chain:
        with patch('tools.graph_query_tool.Neo4jGraph'):
            mock_chain.from_llm.return_value = mock_chain_instance

            from tools.graph_query_tool import create_graph_query_tool
            tool = create_graph_query_tool(MagicMock())
            result = tool.func("Leonardo DiCaprio 演过哪些电影")

            assert result == "查询结果"
            mock_chain_instance.run.assert_called_once()


def test_create_vector_search_tool_returns_tool():
    """测试创建向量搜索工具返回 Tool 实例"""
    with patch('tools.vector_search_tool.Neo4jVector') as mock_vector:
        mock_vector.from_existing_index.return_value = MagicMock()
        mock_vector.from_existing_index.return_value.as_retriever.return_value = MagicMock()

        from tools.vector_search_tool import create_vector_search_tool
        tool = create_vector_search_tool(MagicMock())

        assert tool is not None
        assert tool.name == "vector_search"
        assert "语义搜索" in tool.description


def test_vector_search_tool_invokes_retriever():
    """测试向量搜索工具调用 Retriever"""
    mock_doc = MagicMock()
    mock_doc.page_content = "电影信息"
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [mock_doc]

    with patch('tools.vector_search_tool.Neo4jVector') as mock_vector:
        mock_vector.from_existing_index.return_value.as_retriever.return_value = mock_retriever

        from tools.vector_search_tool import create_vector_search_tool
        tool = create_vector_search_tool(MagicMock())
        result = tool.func("关于太空的电影")

        assert "电影信息" in result
        mock_retriever.invoke.assert_called_once()


def test_vector_search_tool_returns_not_found_when_empty():
    """测试向量搜索工具在无结果时返回提示信息"""
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = []

    with patch('tools.vector_search_tool.Neo4jVector') as mock_vector:
        mock_vector.from_existing_index.return_value.as_retriever.return_value = mock_retriever

        from tools.vector_search_tool import create_vector_search_tool
        tool = create_vector_search_tool(MagicMock())
        result = tool.func("不存在的内容")

        assert "未找到" in result


def test_vector_search_tool_handles_exception():
    """测试向量搜索工具异常处理"""
    mock_retriever = MagicMock()
    mock_retriever.invoke.side_effect = Exception("连接失败")

    with patch('tools.vector_search_tool.Neo4jVector') as mock_vector:
        mock_vector.from_existing_index.return_value.as_retriever.return_value = mock_retriever

        from tools.vector_search_tool import create_vector_search_tool
        tool = create_vector_search_tool(MagicMock())
        result = tool.func("测试异常")

        assert "搜索失败" in result
        assert "连接失败" in result


# [AGC:END]
