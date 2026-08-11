# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
Neo4j 入门教程 - Python 实现
主入口文件 - 按顺序执行所有章节

使用方法:
    python neo4j_tutorial.py          # 执行所有章节
    python neo4j_tutorial.py 1        # 只执行第一部分
    python neo4j_tutorial.py 1 2 3    # 执行指定部分
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from data_init import Neo4jConnection, clear_database


# [AGC:START] tool=Cc author=fangkun
# 章节映射
CHAPTERS = {
    1: ("数据建模", "chapter_01_data_modeling"),
    2: ("创建数据", "chapter_02_create_data"),
    3: ("基础查询", "chapter_03_basic_queries"),
    4: ("模糊查询", "chapter_04_fuzzy_queries"),
    5: ("关系查询", "chapter_05_relationship_queries"),
    6: ("聚合查询", "chapter_06_aggregation_queries"),
    7: ("更新操作", "chapter_07_update_operations"),
    8: ("插入和更新关系", "chapter_08_relationship_operations"),
    9: ("删除操作", "chapter_09_delete_operations"),
    10: ("高级查询", "chapter_10_advanced_queries"),
    11: ("完整练习案例", "chapter_11_exercises"),
}


def run_chapter(chapter_num: int) -> None:
    """
    执行指定章节

    Args:
        chapter_num: 章节编号 (1-11)
    """
    if chapter_num not in CHAPTERS:
        print(f"  [ERROR] 无效的章节编号: {chapter_num}")
        print(f"  [INFO] 可用章节: 1-11")
        return

    chapter_name, module_name = CHAPTERS[chapter_num]
    print(f"\n{'='*80}")
    print(f"  执行第 {chapter_num} 部分: {chapter_name}")
    print(f"{'='*80}")

    # 动态导入并执行章节
    import importlib
    module = importlib.import_module(module_name)

    # 获取章节主函数（排除导入的 main）
    func_name = None
    for name in dir(module):
        if not name.startswith('_') and name != 'main' and callable(getattr(module, name)):
            func = getattr(module, name)
            # 查找主要的执行函数
            if 'queries' in name or 'operations' in name or 'modeling' in name or 'scenarios' in name:
                func_name = name
                break

    if func_name:
        func = getattr(module, func_name)
        func()
    else:
        # 如果没有找到特定函数，尝试调用可能的函数
        for name in ['create_constraints', 'create_movie_nodes', 'create_person_nodes',
                     'create_studio_nodes', 'create_relationships', 'verify_data',
                     'aggregation_queries', 'query_scenarios', 'update_scenarios']:
            if hasattr(module, name):
                func = getattr(module, name)
                func()


def run_all_chapters() -> None:
    """执行所有章节"""
    for chapter_num in sorted(CHAPTERS.keys()):
        run_chapter(chapter_num)


def print_chapter_list() -> None:
    """打印章节列表"""
    print("\n" + "="*80)
    print("  Neo4j 入门教程 - 章节列表")
    print("="*80)
    for num, (name, _) in CHAPTERS.items():
        print(f"  第 {num:2d} 部分: {name}")
    print("="*80)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  Neo4j 入门教程 - Python 实现")
    print("  基于 1.neo4j入门语法.md")
    print("="*80)

    try:
        # 测试连接
        print("\n  [INFO] 测试 Neo4j 连接...")
        result = Neo4jConnection.execute_query("RETURN 1 AS test")
        print(f"  [OK] 连接成功: {result}")

        # 解析命令行参数
        args = sys.argv[1:]

        if args:
            # 执行指定章节
            chapter_nums = [int(arg) for arg in args if arg.isdigit()]
            if chapter_nums:
                print(f"\n  [INFO] 将执行章节: {chapter_nums}")
                for chapter_num in chapter_nums:
                    run_chapter(chapter_num)
            else:
                print_chapter_list()
        else:
            # 清空数据库并执行所有章节
            print("\n  [INFO] 清空数据库...")
            clear_database()
            run_all_chapters()

        print("\n" + "="*80)
        print("  执行完成!")
        print("="*80)

    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭连接
        Neo4jConnection.close()
        print("\n  [INFO] 数据库连接已关闭")


if __name__ == "__main__":
    main()
# [AGC:END]
