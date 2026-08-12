# [AGC:FILE] tool=Cc author=fangkun date=2026-08-12
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# [AGC:START] tool=Cc author=fangkun
@pytest.fixture(autouse=True)
def reset_driver():
    import neo4j_conn
    neo4j_conn._driver = None
    yield
    neo4j_conn._driver = None
# [AGC:END]


# [AGC:START] tool=Cc author=fangkun
class TestGetSession:
    """测试 get_session 上下文管理器"""

    @patch("neo4j_conn.GraphDatabase")
    def test_get_session_returns_session_context(self, mock_gdb):
        from neo4j_conn import get_session

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        with get_session() as session:
            assert session is mock_session

        mock_gdb.driver.assert_called_once()

    @patch("neo4j_conn.GraphDatabase")
    def test_driver_is_singleton(self, mock_gdb):
        import neo4j_conn

        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        with patch.dict(os.environ, {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "test",
            "NEO4J_DATABASE": "neo4j",
        }):
            with neo4j_conn.get_session():
                pass
            with neo4j_conn.get_session():
                pass

        assert mock_gdb.driver.call_count == 1
        neo4j_conn._driver = None

    @patch("neo4j_conn.GraphDatabase")
    def test_session_uses_database_from_env(self, mock_gdb):
        import neo4j_conn

        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        with patch.dict(os.environ, {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "test",
            "NEO4J_DATABASE": "mydb",
        }):
            with neo4j_conn.get_session():
                pass

        mock_driver.session.assert_called_with(database="mydb")
        neo4j_conn._driver = None
# [AGC:END]


# [AGC:START] tool=Cc author=fangkun
class TestCloseDriver:
    """测试 close_driver 函数"""

    @patch("neo4j_conn.GraphDatabase")
    def test_close_driver_closes_and_resets(self, mock_gdb):
        import neo4j_conn

        mock_driver = MagicMock()
        neo4j_conn._driver = mock_driver

        neo4j_conn.close_driver()

        mock_driver.close.assert_called_once()
        assert neo4j_conn._driver is None
    # [AGC:END]
