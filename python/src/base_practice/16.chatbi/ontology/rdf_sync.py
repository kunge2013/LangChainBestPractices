# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
RDF 本体 -> SQLite 同步器

将 RDF 解析结果映射到 SQLite 表结构（ontology_nodes + ontology_edges）。
"""

# [AGC:START] tool=Cc author=fangkun
import json
import sqlite3
import logging
from typing import Dict, Any

from .rdf_parser import RdfOntologyParser

logger = logging.getLogger(__name__)


def sync_rdf_to_sqlite(parser: RdfOntologyParser, db_path: str) -> None:
    """
    将RDF本体数据同步到SQLite数据库。

    映射规则：
    - RDF Individual -> ontology_nodes (concrete_instance)
    - RDF Class -> ontology_nodes (abstract_concept)
    - RDF Object Property -> ontology_edges
    - RDF Datatype Property -> ontology_nodes.attributes (JSON)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM ontology_edges")
        cursor.execute("DELETE FROM ontology_nodes")

        # 1) 创建 Class 对应的抽象概念节点
        for class_name, class_info in parser.classes.items():
            cursor.execute("""
                INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, description)
                VALUES (?, 'abstract_concept', ?, ?, ?)
            """, (class_name, class_name, class_info['label'], class_info['comment']))

        # 2) 创建 Individual 对应的实例节点
        for indiv_name, indiv_info in parser.individuals.items():
            attrs = {}
            for prop_name, prop_value in indiv_info['datatype_props'].items():
                attrs[prop_name] = prop_value

            indiv_type_uri = indiv_info['type']
            if '/' in indiv_type_uri:
                indiv_type_name = indiv_type_uri.rsplit('/', 1)[-1]
            elif '#' in indiv_type_uri:
                indiv_type_name = indiv_type_uri.rsplit('#', 1)[-1]
            else:
                indiv_type_name = indiv_type_uri

            display_name = indiv_info['datatype_props'].get(
                '客户名称',
                indiv_info['datatype_props'].get('城市名称',
                indiv_info['datatype_props'].get('周期名称',
                indiv_info['datatype_props'].get('指标名称',
                indiv_info['datatype_props'].get('概念名称', indiv_name)))))

            description = indiv_info['datatype_props'].get('描述', '')

            cursor.execute("""
                INSERT OR IGNORE INTO ontology_nodes (node_name, node_type, concept_category, display_name, description, attributes)
                VALUES (?, 'concrete_instance', ?, ?, ?, ?)
            """, (indiv_name, indiv_type_name, display_name, description, json.dumps(attrs, ensure_ascii=False)))

        # 3) 创建 Object Property 对应的边
        for indiv_name, indiv_info in parser.individuals.items():
            for rel_name, targets in indiv_info['object_relations'].items():
                obj_prop = parser.object_props.get(rel_name)
                if not obj_prop:
                    logger.warning(f"未找到对象属性定义: {rel_name}")
                    continue

                for target_name in targets:
                    if '/' in target_name:
                        target_clean = target_name.rsplit('/', 1)[-1]
                    elif '#' in target_name:
                        target_clean = target_name.rsplit('#', 1)[-1]
                    else:
                        target_clean = target_name

                    cursor.execute("""
                        INSERT OR IGNORE INTO ontology_edges (parent_id, child_id, relation_type)
                        SELECT p.id, c.id, ?
                        FROM ontology_nodes p, ontology_nodes c
                        WHERE p.node_name = ? AND c.node_name = ?
                    """, (rel_name, indiv_name, target_clean))

        conn.commit()
        logger.info(f"RDF本体同步完成: {db_path}")
        logger.info(f"  - Classes: {len(parser.classes)}")
        logger.info(f"  - Individuals: {len(parser.individuals)}")
        logger.info(f"  - Object Properties (关系): {len(parser.object_props)}")

    except Exception as e:
        conn.rollback()
        logger.error(f"RDF本体同步失败: {e}")
        raise
    finally:
        conn.close()


def build_mapping_tables_from_rdf(parser: RdfOntologyParser):
    """
    从RDF解析结果构建工具函数所需的映射表。
    替代原 ChatBiAgentOntology.py 中的硬编码映射。

    返回:
        (id_to_entity, entity_to_id, city_code_to_name, city_name_to_code)
    """
    id_to_entity = {}
    city_code_to_name = {}

    for indiv_name, indiv_info in parser.individuals.items():
        props = indiv_info['datatype_props']
        indiv_type = indiv_info['type']

        if '客户' in indiv_type:
            customer_id = props.get('客户编号', indiv_name)
            customer_name = props.get('客户名称', indiv_name)
            id_to_entity[customer_id] = customer_name

        if '城市' in indiv_type:
            city_code = props.get('城市编码', '')
            city_name = props.get('城市名称', indiv_name)
            if city_code and city_name:
                city_code_to_name[city_code] = city_name

    entity_to_id = {v: k for k, v in id_to_entity.items()}
    city_name_to_code = {v: k for k, v in city_code_to_name.items()}

    return id_to_entity, entity_to_id, city_code_to_name, city_name_to_code


def build_concept_keyword_map(parser: RdfOntologyParser) -> Dict[str, str]:
    """
    从RDF解析结果构建业务概念关键词映射。
    用于实体抽取时动态匹配概念关键词，替代硬编码。

    返回:
        {关键词: 概念显示名称}
        例: {"一线城市": "一线城市", "华东区": "华东区", "华中区": "华中区"}
    """
    keyword_map: Dict[str, str] = {}

    for indiv_name, indiv_info in parser.individuals.items():
        if '业务概念' not in indiv_info['type']:
            continue

        concept_name = indiv_info['datatype_props'].get('概念名称', '')
        concept_id = indiv_info['datatype_props'].get('概念编号', '')

        if concept_name:
            keyword_map[concept_name] = concept_name

        # 概念编号也作为可匹配关键词
        if concept_id and concept_id != concept_name:
            keyword_map[concept_id] = concept_name

    return keyword_map
# [AGC:END]
