# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
数据初始化模块

提供事实数据和本体数据的统一初始化入口。
"""

# [AGC:START] tool=Cc author=fangkun
from .fact_init import init_fact_db
from .ontology_init import init_ontology_from_rdf


def init_all(
    rdf_file: str = None,
    db_path: str = "chatbi.db",
    init_fact: bool = True,
    init_ontology: bool = True,
):
    """
    统一初始化：事实数据 + 本体数据。

    参数:
        rdf_file: RDF文件路径（None则使用默认路径）
        db_path: 数据库路径
        init_fact: 是否初始化事实数据
        init_ontology: 是否初始化本体数据

    返回:
        {
            "parser": RdfOntologyParser,
            "id_to_entity": dict,
            "entity_to_id": dict,
            "city_code_to_name": dict,
            "city_name_to_code": dict,
            "concept_keyword_map": dict,
        }
    """
    result = {}

    if init_fact:
        init_fact_db(db_path)

    if init_ontology:
        (
            result["parser"],
            result["id_to_entity"],
            result["entity_to_id"],
            result["city_code_to_name"],
            result["city_name_to_code"],
            result["concept_keyword_map"],
        ) = init_ontology_from_rdf(rdf_file, db_path)

    return result


__all__ = [
    'init_fact_db',
    'init_ontology_from_rdf',
    'init_all',
]
# [AGC:END]
