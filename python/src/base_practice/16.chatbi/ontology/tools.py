# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
LangChain工具函数：逻辑扩层
"""

# [AGC:START] tool=Cc author=fangkun
from typing import List
from langchain_core.tools import tool
import os

from .expander import OntologyExpander

# Global configuration (read from environment variables or config files)
DB_PATH = os.environ.get("ONTOLOGY_DB_PATH", "chatbi.db")

# Global model (initialized externally)
model = None


def set_global_model(llm_model):
    """Set global model"""
    global model
    model = llm_model


@tool
def logical_layer_expansion(
    concept_name: str,
    concept_category: str = None,
    return_type: str = "business_name"
) -> List[str]:
    """
    步骤3.3：逻辑扩层。
    将抽象概念扩展为具体的业务名单。

    示例：
        - 输入: "tier1_cities" -> 输出: ["shanghai", "beijing", "guangzhou", "shenzhen"]
        - 输入: "bytedance_group" -> 输出: ["wuhan_toutiao", "wuhan_douyin", "wuhan_feishu"]
        - 输入: "east_china" -> 输出: ["nanjing", "suzhou", "hangzhou", "ningbo", "shanghai"]

    参数:
        concept_name: 抽象概念名称（支持别名，如"一线城市"、"tier1_cities"）
        concept_category: 概念分类（city/customer/region/business），不指定则自动推断
        return_type: 返回类型
            - "business_name": 业务名称（如"上海"）
            - "physical_code": 物理编码（如"021"）
            - "both": 返回字典 {"上海": "021", "北京": "010"}

    返回:
        具体实例的业务名称列表、物理编码列表或字典
    """
    expander = OntologyExpander(
        db_path=DB_PATH,
        model=model,
        enable_llm_reasoning=True if model else False,
        enable_learning_mode=False
    )

    return expander.expand(concept_name, concept_category, return_type=return_type)
# [AGC:END]
