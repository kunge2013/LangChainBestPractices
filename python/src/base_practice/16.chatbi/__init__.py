# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
ChatBI Agent - RDF 本体驱动版本
"""

import os
import sys

# 将当前目录加入 sys.path，使 IDE 能识别 ontology 和 initdb 子包
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# 导出子模块
from .ontology import (
    RdfOntologyParser,
    sync_rdf_to_sqlite,
    build_mapping_tables_from_rdf,
    build_concept_keyword_map,
    OntologyQueryEngine,
    OntologyLLMReasoner,
    OntologyExpander,
    ConceptNameNormalizer,
    logical_layer_expansion,
    set_global_model,
    create_chatbi_tools,
    init_ontology_tables,
)

from .initdb import (
    init_fact_db,
    init_ontology_from_rdf,
    init_all,
)

__all__ = [
    # ontology 模块
    'RdfOntologyParser',
    'sync_rdf_to_sqlite',
    'build_mapping_tables_from_rdf',
    'build_concept_keyword_map',
    'OntologyQueryEngine',
    'OntologyLLMReasoner',
    'OntologyExpander',
    'ConceptNameNormalizer',
    'logical_layer_expansion',
    'set_global_model',
    'create_chatbi_tools',
    'init_ontology_tables',
    # initdb 模块
    'init_fact_db',
    'init_ontology_from_rdf',
    'init_all',
]
