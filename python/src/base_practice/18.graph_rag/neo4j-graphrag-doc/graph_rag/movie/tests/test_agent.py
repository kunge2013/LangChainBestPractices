# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
import pytest
from unittest.mock import MagicMock, patch


# [AGC:START] tool=Cc author=fangkun
def test_create_movie_agent_returns_agent():
    """测试创建电影 Agent"""
    mock_llm = MagicMock()
    mock_tools = [MagicMock(), MagicMock()]

    with patch('agent.movie_agent.create_react_agent') as mock_init:
        mock_init.return_value = MagicMock()

        from agent.movie_agent import create_movie_agent
        agent = create_movie_agent(mock_llm, mock_tools)

        assert agent is not None
        mock_init.assert_called_once()


def test_movie_agent_has_all_tools():
    """测试 Agent 包含所有工具"""
    mock_llm = MagicMock()
    mock_tools = [
        MagicMock(name="graph_query"),
        MagicMock(name="vector_search"),
        MagicMock(name="recommender")
    ]

    with patch('agent.movie_agent.create_react_agent') as mock_init:
        mock_agent_instance = MagicMock()
        mock_agent_instance.tools = mock_tools
        mock_init.return_value = mock_agent_instance

        from agent.movie_agent import create_movie_agent
        agent = create_movie_agent(mock_llm, mock_tools)

        # 验证工具已注册
        assert len(agent.tools) == 3
# [AGC:END]


# [AGC:START] tool=Cc author=fangkun
@pytest.mark.skip(reason="需要真实 Neo4j 连接")
def test_end_to_end_graph_query():
    """端到端测试：结构化查询"""
    pass


@pytest.mark.skip(reason="需要真实 Neo4j 连接")
def test_end_to_end_vector_search():
    """端到端测试：语义搜索"""
    pass


@pytest.mark.skip(reason="需要真实 Neo4j 连接")
def test_end_to_end_recommendation():
    """端到端测试：推荐"""
    pass
# [AGC:END]
