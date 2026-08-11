# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
图查询工具的单元测试
验证 GraphQueryTool 的创建和调用逻辑
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


# [AGC:END]
