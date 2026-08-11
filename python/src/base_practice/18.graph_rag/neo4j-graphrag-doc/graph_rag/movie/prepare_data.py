# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
数据准备脚本：导入图数据并构建向量索引
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, clear_database
from ingestion import ingest_movies_data, create_vector_index, update_movie_embeddings


def prepare_data():
    """准备所有数据"""

    print("="*80)
    print("  数据准备")
    print("="*80)

    try:
        # 测试连接
        print("\n[INFO] 测试 Neo4j 连接...")
        result = Neo4jConnection.execute_query("RETURN 1 AS test")
        print(f"[OK] 连接成功: {result}")

        # 清空数据库
        print("\n[INFO] 清空数据库...")
        clear_database()

        # 导入图数据
        print("\n[INFO] 导入图数据...")
        ingest_movies_data()
        print("[OK] 图数据导入完成")

        # 创建向量索引
        print("\n[INFO] 创建向量索引...")
        create_vector_index()
        print("[OK] 向量索引创建完成")

        # 更新 embedding
        print("\n[INFO] 更新电影 plot_summary embedding...")
        update_movie_embeddings()
        print("[OK] embedding 更新完成")

        print("\n" + "="*80)
        print("  数据准备完成！")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] 数据准备失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        Neo4jConnection.close()
        print("\n[INFO] 数据库连接已关闭")


if __name__ == "__main__":
    prepare_data()
