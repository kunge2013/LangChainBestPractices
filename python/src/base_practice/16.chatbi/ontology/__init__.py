# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
本体逻辑扩层模块

实现ChatBI步骤3.3逻辑扩层功能，支持多类型概念扩层（城市/客户/区域/业务）。

核心组件：
- OntologyQueryEngine: 数据库查询引擎（递归CTE）
- OntologyLLMReasoner: LLM推理引擎（兜底策略）
- OntologyExpander: 混合调度器
- ConceptNameNormalizer: 概念名称标准化器
- logical_layer_expansion: LangChain工具函数

示例：
    >>> from ontology import OntologyExpander
    >>> expander = OntologyExpander("chatbi.db")
    >>> result = expander.expand("tier1_cities", "city")
    >>> print(result)
    ['shanghai', 'beijing', 'guangzhou', 'shenzhen']
"""

# 数据库
from .database import init_ontology_tables, drop_ontology_tables
from .init_data import load_sample_ontology_data

# 核心组件
from .query_engine import OntologyQueryEngine
from .llm_reasoner import OntologyLLMReasoner
from .expander import OntologyExpander

# 工具
from .normalizer import ConceptNameNormalizer
from .tools import logical_layer_expansion, set_global_model

# 异常
OntologyQueryError = OntologyQueryEngine.ConceptNotFoundError
ConceptNotFoundError = OntologyExpander.ConceptNotFoundError

__all__ = [
    # 数据库
    'init_ontology_tables',
    'drop_ontology_tables',
    'load_sample_ontology_data',

    # 核心组件
    'OntologyQueryEngine',
    'OntologyLLMReasoner',
    'OntologyExpander',

    # 工具
    'ConceptNameNormalizer',
    'logical_layer_expansion',
    'set_global_model',

    # 异常
    'OntologyQueryError',
    'ConceptNotFoundError',
]
