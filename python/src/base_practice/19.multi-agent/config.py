# [AGC:FILE] tool=Cc author=fangkun date=2026-08-24
"""可配置参数：模型名、轮数、审查维度、目录等。"""
# [AGC:START] tool=Cc author=fangkun
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Config:
    """工作流配置参数。"""

    # LLM 模型
    developer_model: str = "gpt-4o"
    tester_model: str = "gpt-4o"

    # LLM 配置
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 20000

    # 迭代控制
    max_rounds: int = 5

    # 审查维度
    review_dimensions: list[str] = field(
        default_factory=lambda: ["correctness", "quality", "edge_cases"]
    )

    # 输出目录
    output_dir: str = ""

    # HITL 预留
    enable_hitl: bool = False

    # conda 环境（pytest 运行用）
    conda_env: str = "langchain11"

    # 工作目录（Agent 生成代码的临时目录）
    workspace_dir: str = ""

    def __post_init__(self) -> None:
        """从环境变量加载默认值。"""
        self.developer_model = os.environ.get("OPENAI_MODEL", self.developer_model)
        self.tester_model = os.environ.get("OPENAI_MODEL", self.tester_model)
        self.base_url = os.environ.get("OPENAI_BASE_URL", self.base_url)
        self.api_key = os.environ.get("OPENAI_API_KEY", self.api_key)
        self.temperature = float(os.environ.get("OPENAI_TEMPERATURE", str(self.temperature)))
        self.max_tokens = int(os.environ.get("OPENAI_MAX_TOKENS", str(self.max_tokens)))
        self.max_rounds = int(os.environ.get("MAX_ROUNDS", str(self.max_rounds)))
        self.enable_hitl = os.environ.get("ENABLE_HITL", "").lower() in ("true", "1")
        self.conda_env = os.environ.get("CONDA_ENV", self.conda_env)

        if not self.output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = os.environ.get(
                "OUTPUT_DIR", f"./output/{timestamp}"
            )

        if not self.workspace_dir:
            self.workspace_dir = os.path.join(self.output_dir, "workspace")

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        """从字典创建配置（用于 CLI 参数覆盖）。"""
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known_fields and v is not None}
        return cls(**filtered)
# [AGC:END]
