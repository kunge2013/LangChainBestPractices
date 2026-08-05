# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
RDF 本体解析器

从 RDF/XML 文件中解析本体结构，提取类、属性、关系、实例。
"""

# [AGC:START] tool=Cc author=fangkun
import xml.etree.ElementTree as ET
from typing import Dict, Any

# RDF 命名空间
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'ont': 'http://example.org/ontology/chatbi/',
}


class RdfOntologyParser:
    """
    从 RDF/XML 文件中解析本体结构。

    提取内容：
    - Classes: 实体类型（客户、城市、应收账款等）
    - Datatype Properties: 数据属性（客户编号、城市名称等）
    - Object Properties: 对象属性/关系（属于城市、拥有账款等）
    - Individuals: 实例数据（具体客户、城市、账款记录等）
    """

    def __init__(self, rdf_file: str):
        self.rdf_file = rdf_file
        self.tree = ET.parse(rdf_file)
        self.root = self.tree.getroot()

        # 解析结果
        self.classes: Dict[str, Dict[str, Any]] = {}
        self.datatype_props: Dict[str, Dict[str, Any]] = {}
        self.object_props: Dict[str, Dict[str, Any]] = {}
        self.individuals: Dict[str, Dict[str, Any]] = {}

    def parse(self) -> 'RdfOntologyParser':
        """执行完整解析，返回自身以便链式调用。"""
        self._parse_classes()
        self._parse_datatype_properties()
        self._parse_object_properties()
        self._parse_individuals()
        return self

    def _parse_classes(self):
        """解析所有 owl:Class 定义。"""
        for cls in self.root.findall('.//owl:Class', NS):
            about = cls.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', '')
            label_el = cls.find('rdfs:label', NS)
            comment_el = cls.find('rdfs:comment', NS)
            icon_el = cls.find('ont:icon', NS)
            color_el = cls.find('ont:color', NS)

            name = about.strip()
            self.classes[name] = {
                'label': label_el.text.strip() if label_el is not None else name,
                'comment': comment_el.text.strip() if comment_el is not None else '',
                'icon': icon_el.text.strip() if icon_el is not None else '',
                'color': color_el.text.strip() if color_el is not None else '',
            }

    def _parse_datatype_properties(self):
        """解析所有 owl:DatatypeProperty 定义。"""
        for prop in self.root.findall('.//owl:DatatypeProperty', NS):
            about = prop.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', '')
            label_el = prop.find('rdfs:label', NS)
            domain_el = prop.find('rdfs:domain', NS)
            range_el = prop.find('rdfs:range', NS)
            prop_type_el = prop.find('ont:propertyType', NS)
            is_id_el = prop.find('ont:isIdentifier', NS)
            unit_el = prop.find('ont:unit', NS)

            name = about.strip()
            domain_ref = domain_el.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '') if domain_el is not None else ''
            range_ref = range_el.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '') if range_el is not None else ''

            self.datatype_props[name] = {
                'label': label_el.text.strip() if label_el is not None else name,
                'domain': domain_ref,
                'range': range_ref,
                'propertyType': prop_type_el.text.strip() if prop_type_el is not None else 'string',
                'isIdentifier': is_id_el is not None and is_id_el.text.strip().lower() == 'true',
                'unit': unit_el.text.strip() if unit_el is not None else '',
            }

    def _parse_object_properties(self):
        """解析所有 owl:ObjectProperty 定义（关系）。"""
        for prop in self.root.findall('.//owl:ObjectProperty', NS):
            about = prop.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', '')
            label_el = prop.find('rdfs:label', NS)
            domain_el = prop.find('rdfs:domain', NS)
            range_el = prop.find('rdfs:range', NS)
            comment_el = prop.find('rdfs:comment', NS)
            card_el = prop.find('ont:cardinality', NS)
            from_el = prop.find('ont:fromEntityId', NS)
            to_el = prop.find('ont:toEntityId', NS)

            name = about.strip()
            domain_ref = domain_el.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '') if domain_el is not None else ''
            range_ref = range_el.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '') if range_el is not None else ''

            self.object_props[name] = {
                'label': label_el.text.strip() if label_el is not None else name,
                'domain': domain_ref,
                'range': range_ref,
                'cardinality': card_el.text.strip() if card_el is not None else '',
                'fromEntityId': from_el.text.strip() if from_el is not None else domain_ref,
                'toEntityId': to_el.text.strip() if to_el is not None else range_ref,
                'comment': comment_el.text.strip() if comment_el is not None else '',
            }

    def _parse_individuals(self):
        """解析所有 owl:NamedIndividual 实例。"""
        for indiv in self.root.findall('.//owl:NamedIndividual', NS):
            about = indiv.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', '')
            name = about.strip()

            type_el = indiv.find('rdf:type', NS)
            indiv_type = type_el.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '') if type_el is not None else ''

            datatype_props = {}
            object_relations = {}

            for child in indiv:
                tag = child.tag
                if tag == '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}type':
                    continue

                local_name = tag.split('}', 1)[1] if '}' in tag else tag

                resource_ref = child.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                if resource_ref is not None:
                    if local_name not in object_relations:
                        object_relations[local_name] = []
                    object_relations[local_name].append(resource_ref)
                else:
                    datatype_props[local_name] = child.text.strip() if child.text else ''

            self.individuals[name] = {
                'type': indiv_type,
                'datatype_props': datatype_props,
                'object_relations': object_relations,
            }
# [AGC:END]
