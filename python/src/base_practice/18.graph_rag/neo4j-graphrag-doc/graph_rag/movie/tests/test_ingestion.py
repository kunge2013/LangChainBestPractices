# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
图数据导入模块的单元测试
验证电影、人物、制片厂数据导入逻辑
"""
import pytest
from unittest.mock import patch, MagicMock


# [AGC:START] tool=Cc author=fangkun


def test_ingest_movies_data_creates_nodes():
    """测试数据导入创建节点"""
    with patch('ingestion.ingest_graph.Neo4jConnection') as mock_conn:
        from ingestion.ingest_graph import ingest_movies_data
        ingest_movies_data()

        # 验证调用了 execute_write 方法创建节点和关系
        assert mock_conn.execute_write.called
        # execute_write 被调用次数:
        # 3 部电影 + 6 个人物 + 3 个制片厂 + 18 个关系 = 30 次
        assert mock_conn.execute_write.call_count == 30


def test_ingest_movies_data_movie_nodes():
    """测试电影节点创建"""
    with patch('ingestion.ingest_graph.Neo4jConnection') as mock_conn:
        from ingestion.ingest_graph import ingest_movies_data
        ingest_movies_data()

        # 验证 MERGE 电影查询被调用（前 3 次调用是电影节点）
        calls = mock_conn.execute_write.call_args_list
        movie_queries = [
            call for call in calls[:3]
            if 'MERGE (m:Movie' in call.args[0]
        ]
        assert len(movie_queries) == 3


def test_ingest_movies_data_person_nodes():
    """测试人物节点创建"""
    with patch('ingestion.ingest_graph.Neo4jConnection') as mock_conn:
        from ingestion.ingest_graph import ingest_movies_data
        ingest_movies_data()

        calls = mock_conn.execute_write.call_args_list
        # 人物节点在第 4-9 次调用（3 部电影之后）
        person_queries = [
            call for call in calls[3:9]
            if 'MERGE (p:Person' in call.args[0]
        ]
        assert len(person_queries) == 6


def test_ingest_movies_data_studio_nodes():
    """测试制片厂节点创建"""
    with patch('ingestion.ingest_graph.Neo4jConnection') as mock_conn:
        from ingestion.ingest_graph import ingest_movies_data
        ingest_movies_data()

        calls = mock_conn.execute_write.call_args_list
        # 制片厂节点在第 10-12 次调用（3 部电影 + 6 个人物之后）
        studio_queries = [
            call for call in calls[9:12]
            if 'MERGE (s:Studio' in call.args[0]
        ]
        assert len(studio_queries) == 3


def test_ingest_movies_data_relationships():
    """测试关系创建"""
    with patch('ingestion.ingest_graph.Neo4jConnection') as mock_conn:
        from ingestion.ingest_graph import ingest_movies_data
        ingest_movies_data()

        calls = mock_conn.execute_write.call_args_list
        # 关系从第 13 次调用开始
        relationship_queries = [
            call for call in calls[12:]
            if 'MERGE (p)-[r:' in call.args[0]
        ]
        assert len(relationship_queries) == 18


def test_ingest_movies_data_acted_in_relationship():
    """测试 ACTED_IN 关系包含角色信息"""
    with patch('ingestion.ingest_graph.Neo4jConnection') as mock_conn:
        from ingestion.ingest_graph import ingest_movies_data
        ingest_movies_data()

        calls = mock_conn.execute_write.call_args_list
        # 第一个关系是 Leonardo DiCaprio ACTED_IN Inception
        first_rel_call = calls[12]
        query = first_rel_call.args[0]
        params = first_rel_call.args[1]

        assert 'ACTED_IN' in query
        assert params['person_name'] == 'Leonardo DiCaprio'
        assert params['movie_title'] == 'Inception'
        assert params['props'] == {'roles': ['Cobb']}


def test_create_vector_index_calls_neo4j():
    """测试向量索引创建调用 Neo4j"""
    with patch('ingestion.ingest_vectors.Neo4jConnection') as mock_conn:
        from ingestion.ingest_vectors import create_vector_index
        create_vector_index()

        # 验证调用了 execute_write 方法创建索引
        assert mock_conn.execute_write.called
        # 验证传入的查询包含向量索引创建语句
        call_args = mock_conn.execute_write.call_args
        query = call_args.args[0]
        assert 'CREATE VECTOR INDEX' in query
        assert 'movie_plot_summary_index' in query
        assert 'vector.dimensions' in query
        assert '384' in query


def test_create_vector_index_query_content():
    """测试向量索引查询语句包含正确的配置"""
    with patch('ingestion.ingest_vectors.Neo4jConnection') as mock_conn:
        from ingestion.ingest_vectors import create_vector_index
        create_vector_index()

        call_args = mock_conn.execute_write.call_args
        query = call_args.args[0]
        assert 'cosine' in query
        assert 'plot_summary_embedding' in query


def test_update_movie_embeddings_generates_and_stores():
    """测试电影 embedding 更新流程"""
    with patch('ingestion.ingest_vectors.Neo4jConnection') as mock_conn:
        # 模拟查询返回的电影数据
        mock_conn.execute_query.return_value = [
            {"title": "Inception", "plot_summary": "A thief who steals corporate secrets"},
            {"title": "Movie Without Summary", "plot_summary": None},
        ]

        with patch('ingestion.ingest_vectors.HuggingFaceEmbeddings') as mock_embeddings_cls:
            mock_embeddings_instance = MagicMock()
            mock_embeddings_instance.embed_query.return_value = [0.1] * 384
            mock_embeddings_cls.return_value = mock_embeddings_instance

            from ingestion.ingest_vectors import update_movie_embeddings
            update_movie_embeddings()

            # 验证只对有 plot_summary 的电影调用了 embed_query
            assert mock_embeddings_instance.embed_query.call_count == 1
            # 验证 execute_write 被调用（只有 Inception 被更新）
            write_calls = mock_conn.execute_write.call_args_list
            # 第一次写入是 update_movie_embeddings 的 SET embedding 调用
            assert len(write_calls) == 1
            params = write_calls[0].args[1]
            assert params["title"] == "Inception"
            assert len(params["embedding"]) == 384


# [AGC:END]
