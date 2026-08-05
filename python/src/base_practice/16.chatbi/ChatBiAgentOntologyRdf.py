# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
ChatBiAgentOntologyRdf - 基于RDF本体的ChatBI Agent

从 chatbi.rdf 文件解析本体结构，驱动SQLite本体数据库的初始化与查询。
"""

# [AGC:START] tool=Cc author=fangkun
import os
import sys
import logging
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ======================== 日志 ========================
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s', datefmt='%H:%M:%S')
)
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)
logging.getLogger('deepagents').setLevel(logging.WARNING)

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logger.info("init start")
print("init start", flush=True)

# ======================== 导入模块 ========================
from ontology.rdf_parser import RdfOntologyParser
from ontology.tools import logical_layer_expansion, set_global_model
from ontology.chatbi_tools import create_chatbi_tools
from initdb import init_all

# ======================== 路径 ========================
RDF_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rdf", "chatbi.rdf")
DB_PATH = "chatbi.db"

# ======================== 初始化 ========================
parser = None
ID_TO_ENTITY = {}
ENTITY_TO_ID = {}
CITY_CODE_TO_NAME = {}
CITY_NAME_TO_CODE = {}
CONCEPT_KEYWORD_MAP = {}

if os.environ.get("init_db", "True").lower() == 'true':
    data = init_all(RDF_FILE, DB_PATH)
    parser = data["parser"]
    ID_TO_ENTITY = data["id_to_entity"]
    ENTITY_TO_ID = data["entity_to_id"]
    CITY_CODE_TO_NAME = data["city_code_to_name"]
    CITY_NAME_TO_CODE = data["city_name_to_code"]
    CONCEPT_KEYWORD_MAP = data["concept_keyword_map"]
elif os.path.exists(RDF_FILE):
    parser = RdfOntologyParser(RDF_FILE).parse()
    from ontology.rdf_sync import build_mapping_tables_from_rdf, build_concept_keyword_map
    ID_TO_ENTITY, ENTITY_TO_ID, CITY_CODE_TO_NAME, CITY_NAME_TO_CODE = build_mapping_tables_from_rdf(parser)
    CONCEPT_KEYWORD_MAP = build_concept_keyword_map(parser)


# ======================== 工具 & LLM ========================
tools = create_chatbi_tools(
    entity_to_id=ENTITY_TO_ID,
    city_name_to_code=CITY_NAME_TO_CODE,
    city_code_to_name=CITY_CODE_TO_NAME,
    fact_db_path=DB_PATH,
    concept_keyword_map=CONCEPT_KEYWORD_MAP,
)
tools.insert(1, logical_layer_expansion)

model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASEURL", os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")),
    api_key=os.environ.get("OPENAI_API_KEY", "sk-xxx"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.0")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "1024")),
)
set_global_model(model)


# ======================== System Prompt ========================
def _build_system_prompt(p: Optional[RdfOntologyParser] = None) -> str:
    """动态构建system prompt，注入RDF本体信息。"""
    base = """你是一个 ChatBI 助手，专门查询企业应收款和营收数据。
你集成了基于RDF本体的逻辑扩层功能，支持多种业务概念的智能扩展。

请严格按照以下步骤执行：

步骤1：实体抽取
- 调用 extract_entities_enhanced 从用户输入中提取实体（时间、地点、概念、指标）
- 概念可以是抽象的，如"一线城市"、"华东区"等

步骤2：本体逻辑扩层
- 调用 logical_layer_expansion 进行概念扩层
- 将抽象概念扩展为具体的业务名称列表
- 参数说明：
  - concept_name: 抽象概念名称
  - concept_category: 概念分类（city/customer/region/business），不指定则自动推断
  - return_type: 返回类型
    - "business_name": 返回业务名称列表
    - "physical_code": 返回物理编码列表
    - "both": 返回映射字典

步骤3：指标映射
- 调用 map_metric 获取指标对应的 SQL 聚合表达式

步骤4：维度映射
- 调用 map_dimension 获取维度对应的逻辑字段名

步骤5：组装逻辑 SQL
- 调用 assemble_logical_sql 生成逻辑 SQL

步骤6：执行 SQL
- 调用 execute_sql 执行最终 SQL 并获取数值

步骤7：结果校验
- 调用 validate_result 校验结果是否合理

步骤8：返回答案
- 如果校验通过，给出自然语言答案，包含格式化金额
- 如果校验失败，提示用户数据异常

若某一步缺少必要参数，应主动向用户追问。
"""
    if p is None:
        return base

    sections = [base, "\n=== 当前本体知识库 ===\n"]

    sections.append("\n【实体类型】")
    for cls_name, cls_info in p.classes.items():
        sections.append(f"- {cls_info['label']} ({cls_name}): {cls_info['comment']}")

    sections.append("\n【业务概念】")
    for indiv_name, indiv_info in p.individuals.items():
        if '业务概念' in indiv_info['type']:
            concept_name = indiv_info['datatype_props'].get('概念名称', indiv_name)
            desc = indiv_info['datatype_props'].get('描述', '')
            includes_cities = indiv_info['object_relations'].get('包含城市', [])
            includes_customers = indiv_info['object_relations'].get('包含客户', [])
            city_names = [c.rsplit('/', 1)[-1] if '/' in c else c for c in includes_cities]
            customer_names = [c.rsplit('/', 1)[-1] if '/' in c else c for c in includes_customers]
            detail = ""
            if city_names:
                detail += f" 包含城市: {', '.join(city_names)}"
            if customer_names:
                detail += f" 包含客户: {', '.join(customer_names)}"
            sections.append(f"- {concept_name}: {desc}{detail}")

    sections.append("\n【城市】")
    for indiv_name, indiv_info in p.individuals.items():
        if '城市' in indiv_info['type']:
            cn = indiv_info['datatype_props'].get('城市名称', indiv_name)
            cc = indiv_info['datatype_props'].get('城市编码', '')
            sections.append(f"- {cn} (编码: {cc})")

    return "\n".join(sections)


system_prompt = _build_system_prompt(parser)


# ======================== Agent ========================
agent = create_deep_agent(
    model=model,
    tools=tools,
    system_prompt=SystemMessage(content=system_prompt)
)


# ======================== 测试 ========================
def test_ask_question(user_input: str):
    """测试Agent对话"""
    print(f"👤 用户: {user_input}\n")
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    final_message = result["messages"][-1]
    final_answer = final_message.content

    print("=" * 60)
    print("🧠 完整执行链路追踪（工具调用顺序）")
    print("=" * 60)
    for msg in result["messages"]:
        if msg.type == "human":
            print(f"👤 用户: {msg.content}")
        elif msg.type == "ai":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"🤖 调用工具: {tc['name']} 参数: {tc['args']}")
            else:
                print(f"🤖 最终回答: {msg.content}")
        elif msg.type == "tool":
            print(f"🔧 工具 {msg.name} 返回: {msg.content}")
    print("=" * 60)
    print(f"\n💬 最终回复: {final_answer}")

    return result

#
# if __name__ == "__main__":
#     if parser:
#         print("\n=== RDF 本体解析结果 ===")
#         print(f"实体类型 ({len(parser.classes)}):")
#         for name, info in parser.classes.items():
#             print(f"  - {info['label']} ({name})")
#
#         print(f"\n对象属性/关系 ({len(parser.object_props)}):")
#         for name, info in parser.object_props.items():
#             print(f"  - {info['label']} ({name}): {info['fromEntityId']} -> {info['toEntityId']}")
#
#         print(f"\n实例 ({len(parser.individuals)}):")
#         for name, info in parser.individuals.items():
#             type_name = info['type'].rsplit('/', 1)[-1] if '/' in info['type'] else info['type']
#             print(f"  - {name} (类型: {type_name})")
#
#         print(f"\n概念关键词映射 ({len(CONCEPT_KEYWORD_MAP)}):")
#         for kw, display in CONCEPT_KEYWORD_MAP.items():
#             print(f"  {kw} -> {display}")
#         print()
#
#     test_cases = [
#         "一线城市上个月应收多少",
#         "华东区本月营收如何",
#     ]
#
#     for question in test_cases:
#         print("\n" + "=" * 80)
#         test_ask_question(question)
#         print("\n")
# [AGC:END]
