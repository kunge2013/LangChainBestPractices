from rdflib import Graph, URIRef, XSD
from rdflib.namespace import RDF, OWL, RDFS, DefinedNamespace, Namespace
from neo4j_graphrag.experimental.components.schema import (
    SchemaBuilder,
    NodeType,           # 替代 SchemaEntity
    PropertyType,       # 替代 SchemaProperty
    RelationshipType,   # 替代 SchemaRelation
    GraphSchema         # 替代 SchemaConfig
)


def getLocalPart(uri):
    pos = -1
    pos = uri.rfind('#')
    if pos < 0:
        pos = uri.rfind('/')
    if pos < 0:
        pos = uri.rindex(':')
    return uri[pos+1:]


def getNLOntology(g):
    result = ''
    definedcats = []

    result += '\nNode Labels:\n'
    for cat in g.subjects(RDF.type, OWL.Class):
        result += getLocalPart(cat)
        definedcats.append(cat)
        for desc in g.objects(cat, RDFS.comment):
            result += ': ' + desc + '\n'

    extracats = {}
    for cat in g.objects(None, RDFS.domain):
        if cat not in definedcats:
            extracats[cat] = None
    for cat in g.objects(None, RDFS.range):
        if not (cat.startswith("http://www.w3.org/2001/XMLSchema#") or cat in definedcats):
            extracats[cat] = None

    for xtracat in extracats.keys():
        result += getLocalPart(cat) + ":\n"

    result += '\nNode Properties:\n'
    for att in g.subjects(RDF.type, OWL.DatatypeProperty):
        result += getLocalPart(att)
        for dom in g.objects(att, RDFS.domain):
            result += ': Attribute that applies to entities of type ' + getLocalPart(dom)
        for desc in g.objects(att, RDFS.comment):
            result += '. It represents ' + desc + '\n'

    result += '\nRelationships:\n'
    for att in g.subjects(RDF.type, OWL.ObjectProperty):
        result += getLocalPart(att)
        for dom in g.objects(att, RDFS.domain):
            result += ': Relationship that connects entities of type ' + getLocalPart(dom)
        for ran in g.objects(att, RDFS.range):
            result += ' to entities of type ' + getLocalPart(ran)
        for desc in g.objects(att, RDFS.comment):
            result += '. It represents ' + desc + '\n'
    return result


def getPropertiesForClass(g, cat):
    props = []
    for dtp in g.subjects(RDFS.domain, cat):
        if (dtp, RDF.type, OWL.DatatypeProperty) in g:
            propName = getLocalPart(dtp)
            propDesc = next(g.objects(dtp, RDFS.comment), "")
            props.append(PropertyType(  # 使用 PropertyType 替代 SchemaProperty
                name=propName,
                type=convert_to_di_data_type(next(g.objects(dtp, RDFS.range), "")),
                description=propDesc
            ))
    return props


async def getSchemaFromOnto(path) -> GraphSchema:  # 改为 async 函数
    g = Graph()
    g.parse(path)
    schema_builder = SchemaBuilder()
    classes = {}
    node_types = []      # 替代 entities
    relationship_types = []  # 替代 rels
    patterns = []        # 替代 triples (potential_schema)

    # 处理 OWL.Class
    for cat in g.subjects(RDF.type, OWL.Class):
        classes[cat] = None
        label = getLocalPart(cat)
        props = getPropertiesForClass(g, cat)
        if not props:
            # NodeType.properties requires at least 1 item (MinLen=1); skip abstract/base classes
            continue
        node_types.append(NodeType(  # 使用 NodeType 替代 SchemaEntity
            label=label,
            description=str(next(g.objects(cat, RDFS.comment), "")),
            properties=props
        ))

    # 处理 RDFS.domain 中出现的类
    for cat in g.objects(None, RDFS.domain):
        if cat not in classes.keys():
            classes[cat] = None
            label = getLocalPart(cat)
            props = getPropertiesForClass(g, cat)
            if not props:
                continue
            node_types.append(NodeType(
                label=label,
                description=str(next(g.objects(cat, RDFS.comment), "")),
                properties=props
            ))

    # 处理 RDFS.range 中出现的类（排除 XML Schema 类型）
    for cat in g.objects(None, RDFS.range):
        if not (cat.startswith("http://www.w3.org/2001/XMLSchema#") or cat in classes.keys()):
            classes[cat] = None
            label = getLocalPart(cat)
            props = getPropertiesForClass(g, cat)
            if not props:
                continue
            node_types.append(NodeType(
                label=label,
                description=str(next(g.objects(cat, RDFS.comment), "")),
                properties=props
            ))

            # 处理对象属性作为关系
    for op in g.subjects(RDF.type, OWL.ObjectProperty):
        relname = getLocalPart(op)
        relationship_types.append(RelationshipType(  # 使用 RelationshipType 替代 SchemaRelation
            label=relname,
            properties=[],  # 关系属性通常为空，可以根据需要扩展
            description=next(g.objects(op, RDFS.comment), "")
        ))

    # 构建关系模式 (patterns)
    for op in g.subjects(RDF.type, OWL.ObjectProperty):
        relname = getLocalPart(op)
        doms = []
        rans = []
        for dom in g.objects(op, RDFS.domain):
            if dom in classes.keys():
                doms.append(getLocalPart(dom))
        for ran in g.objects(op, RDFS.range):
            if ran in classes.keys():
                rans.append(getLocalPart(ran))
        for d in doms:
            for r in rans:
                patterns.append((d, relname, r))  # patterns 替代 triples

    # 使用新的 API: run 方法替代 create_schema_model
    return await schema_builder.run(
        node_types=node_types,           # 新参数名
        relationship_types=relationship_types,  # 新参数名
        patterns=patterns                # 新参数名 (替代 potential_schema)
    )


def getPKs(g):
    keys = []
    for k in g.subjects(RDF.type, OWL.InverseFunctionalProperty):
        keys.append(getLocalPart(k))
    return keys


def convert_to_di_data_type(datatype):
    if datatype in {XSD.integer, XSD.int, XSD.positiveInteger, XSD.negativeInteger, XSD.nonPositiveInteger,
                    XSD.nonNegativeInteger, XSD.long, XSD.short, XSD.unsignedLong, XSD.unsignedShort}:
        return "INTEGER"
    elif datatype in {XSD.decimal, XSD.float, XSD.double}:
        return "FLOAT"
    elif datatype == XSD.boolean:
        return "BOOLEAN"
    # elif datatype == XSD.dateTime:
    #     return "LOCAL_DATETIME"
    else:
        return "STRING"