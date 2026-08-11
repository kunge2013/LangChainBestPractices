# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
"""
测试配置模块
设置 Python 路径以便测试可以导入项目模块
"""
import sys
import os

# [AGC:START] tool=Cc author=fangkun

# 将 movie 目录添加到 Python 路径
movie_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if movie_dir not in sys.path:
    sys.path.insert(0, movie_dir)

# [AGC:END]
