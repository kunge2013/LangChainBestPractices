# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
本体数据初始化

从 RDF 文件解析本体结构，同步到 SQLite 数据库。
"""

# [AGC:START] tool=Cc author=fangkun
import os
import logging

# 父目录加入 sys.path，使 IDE 和运行时都能识别 ontology 兄弟包


from ontology.rdf_parser import RdfOntologyParser
from ontology.rdf_sync import sync_rdf_to_sqlite, build_mapping_tables_from_rdf, build_concept_keyword_map
from ontology.database import init_ontology_tables

logger = logging.getLogger(__name__)


def init_ontology_from_rdf(
    rdf_file: str = None,
    db_path: str = "chatbi.db",
):
    """
    从RDF文件初始化本体数据库。

    参数:
        rdf_file: RDF文件路径，默认查找项目 rdf/ 目录下的 chatbi.rdf
        db_path: 数据库路径

    返回:
        (parser, id_to_entity, entity_to_id, city_code_to_name, city_name_to_code, concept_keyword_map)
    """
    if rdf_file is None:
        rdf_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rdf", "chatbi.rdf")

    init_ontology_tables(db_path)

    parser = RdfOntologyParser(rdf_file).parse()
    sync_rdf_to_sqlite(parser, db_path)
    logger.info(f"本体数据库（RDF驱动）初始化完成: {db_path}")
    print("✅ 本体数据库（RDF驱动）初始化完成。")

    id_to_entity, entity_to_id, city_code_to_name, city_name_to_code = build_mapping_tables_from_rdf(parser)
    concept_keyword_map = build_concept_keyword_map(parser)

    return parser, id_to_entity, entity_to_id, city_code_to_name, city_name_to_code, concept_keyword_map
# [AGC:END]
