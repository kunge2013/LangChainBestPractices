#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直接测试多 Agent 协同开发模块"""

# 修复 OpenMP 库冲突问题
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
from pathlib import Path

# 添加当前目录到路径
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from dotenv import load_dotenv
load_dotenv(override=True)

from config import Config
from graph import build_graph
from models import WorkflowStatus

def test_workflow():
    """测试完整工作流"""

    # 设计文档路径
    design_doc_path = r"D:\doc\天源迪科\design\jtbill\raw\design\jtbill\Ledger_BILL\design\权责销账功能-详细设计文档-2026-08-17.md"

    # 验证文件存在
    if not os.path.exists(design_doc_path):
        print(f"ERROR: 设计文档不存在: {design_doc_path}")
        return

    print(f"[OK] 设计文档存在: {design_doc_path}")
    print(f"   文件大小: {os.path.getsize(design_doc_path)} 字节")

    # 创建配置
    config = Config(
        output_dir="./test_output_direct",
        max_rounds=3
    )

    print(f"\n[CONFIG] 配置信息:")
    print(f"   输出目录: {config.output_dir}")
    print(f"   最大轮数: {config.max_rounds}")
    print(f"   模型: {config.developer_model}")

    # 构建图
    print(f"\n[BUILD] 构建状态图...")
    graph = build_graph(config)
    print(f"[OK] 状态图构建成功")

    # 准备初始状态
    initial_state = {
        "messages": [],
        "design_doc": design_doc_path,
        "requirement": "请直接测试",
        "code_artifact": {},
        "test_results": {},
        "bug_list": [],
        "iteration_count": 0,
        "max_rounds": config.max_rounds,
        "status": WorkflowStatus.IN_PROGRESS.value,
        "output_dir": config.output_dir,
        "review_dimensions": config.review_dimensions,
        "iteration_history": [],
    }

    print("\n[START] Begin workflow...")
    print("=" * 60)

    try:
        # 运行工作流
        final_state = graph.invoke(initial_state)

        print("\n" + "=" * 60)
        print("[DONE] workflow completed")
        print(f"   final status: {final_state.get('status')}")
        print(f"   iterations: {final_state.get('iteration_count')}")
        print(f"   generated files: {len(final_state.get('code_artifact', {}))}")

        # 显示生成的文件
        code_artifacts = final_state.get('code_artifact', {})
        if code_artifacts:
            print("\n[FILES] Generated files:")
            for filepath in code_artifacts.keys():
                print(f"   - {filepath}")

        # 显示测试历史
        history = final_state.get('iteration_history', [])
        if history:
            print("\n[HISTORY] Iteration history:")
            for record in history:
                print(f"   Round {record['round_number']}: "
                      f"CRITICAL={record['critical_count']}, "
                      f"HIGH={record['high_count']}, "
                      f"LOW={record['low_count']}")

        print(f"\n[OUTPUT] output dir: {config.output_dir}")
        return final_state

    except Exception as e:
        print(f"\n[ERROR] workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_workflow()
