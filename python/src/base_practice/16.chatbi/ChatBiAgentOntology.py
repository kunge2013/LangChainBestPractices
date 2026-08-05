# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
ChatBiAgentNotology - 集成本体逻辑扩层功能的ChatBI Agent

这个Agent集成了新实现的本体逻辑扩层功能，支持：
- 基于SQLite递归CTE的本体图结构
- 多类型概念扩层（城市/客户/区域）
- 混合策略（数据库查询 + LLM推理兜底）
- 可选学习模式（LLM推理结果回写数据库）
"""

# [AGC:START] tool=Cc author=fangkun
import os
import sys
import re
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 将当前脚本所在目录加入 sys.path，确保能正确导入 ontology 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ======================== 配置日志输出到控制台 ========================
# 创建控制台 handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s', datefmt='%H:%M:%S')
)

# 配置根 logger，确保所有子模块的 logger 都能输出到控制台
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)

# 抑制 deepagents 的 DEBUG 级别日志（Bedrock 中间件未安装的报错）
logging.getLogger('deepagents').setLevel(logging.WARNING)

# Windows GBK encoding fix - 使用 line_buffering 实现实时输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logger.info("init start")
print("init start", flush=True)
# ======================== 1. 初始化 LLM ========================
model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "sk-xxx"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.0")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "1024")),
)

# ======================== 2. 初始化数据库 ========================
FACT_DB_PATH = "chatbi.db"
ONTOLOGY_DB_PATH = "chatbi.db"  # 本体数据库与事实数据库共用

# 初始化事实数据表
def init_fact_db():
    """初始化事实数据表（应收款数据）"""
    conn = sqlite3.connect(FACT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_account_receivable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            city_code TEXT NOT NULL,
            date TEXT NOT NULL,
            balance REAL NOT NULL
        )
    ''')
    cursor.execute("DELETE FROM fact_account_receivable")

    # 插入测试数据
    sample_data = [
        ("CUST_SH_001", "021", "2026-07-15", 18234500.00),  # 上海
        ("CUST_SH_001", "021", "2026-07-20", 12456700.00),
        ("CUST_BJ_002", "010", "2026-07-10", 15678900.00),  # 北京
        ("CUST_BJ_002", "010", "2026-07-25", 18765400.00),
        ("CUST_GZ_003", "020", "2026-07-05", 12456000.00),  # 广州
        ("CUST_GZ_003", "020", "2026-07-18", 14567000.00),
        ("CUST_SZ_004", "0755", "2026-07-12", 16789000.00),  # 深圳
        ("CUST_SZ_004", "0755", "2026-07-22", 18923000.00),
        ("CUST_HZ_005", "0571", "2026-07-08", 13456000.00),  # 杭州
        ("CUST_HZ_005", "0571", "2026-07-19", 15678000.00),
    ]
    cursor.executemany(
        "INSERT INTO fact_account_receivable (customer_id, city_code, date, balance) VALUES (?,?,?,?)",
        sample_data
    )
    conn.commit()
    conn.close()
    print("✅ 事实数据表初始化完成。")

# 初始化本体数据库
def init_ontology_db():
    """初始化本体数据库"""
    from ontology import init_ontology_tables, load_sample_ontology_data

    init_ontology_tables(ONTOLOGY_DB_PATH)
    load_sample_ontology_data(ONTOLOGY_DB_PATH)
    print("✅ 本体数据库初始化完成。")

# 初始化所有数据库
if os.environ.get("init_db", "True").lower() == 'true':
    init_fact_db()
    init_ontology_db()

# ======================== 3. 物理映射表 ========================
# 客户ID → 业务名称映射（用于结果显示）
ID_TO_ENTITY = {
    "CUST_SH_001": "上海分公司A",
    "CUST_BJ_002": "北京分公司B",
    "CUST_GZ_003": "广州分公司C",
    "CUST_SZ_004": "深圳分公司D",
    "CUST_HZ_005": "杭州分公司E",
}

# 业务名称 → 客户ID映射（用于SQL生成）
ENTITY_TO_ID = {v: k for k, v in ID_TO_ENTITY.items()}

# 城市编码 → 城市名称映射（用于结果显示）
CITY_CODE_TO_NAME = {
    "021": "上海",
    "010": "北京",
    "020": "广州",
    "0755": "深圳",
    "0571": "杭州",
}

# 城市名称 → 城市编码映射（用于SQL生成）
CITY_NAME_TO_CODE = {v: k for k, v in CITY_CODE_TO_NAME.items()}

# ======================== 4. 工具函数 ========================

@tool
def extract_entities_enhanced(query: str) -> dict:
    """
    步骤1：增强型实体抽取。
    从用户查询中提取时间、地点、概念、指标。

    参数:
        query: 用户查询文本

    返回:
        实体字典：{"time": ..., "date_start": ..., "date_end": ..., "location": ..., "concept": ..., "metric": ...}
    """
    # 时间抽取
    now = datetime(2026, 8, 4)
    if "上个月" in query:
        first_day = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day = now.replace(day=1) - timedelta(days=1)
        date_start = first_day.strftime("%Y-%m-%d")
        date_end = last_day.strftime("%Y-%m-%d")
        time_desc = "上个月"
    elif "本月" in query:
        date_start = now.replace(day=1).strftime("%Y-%m-%d")
        date_end = now.strftime("%Y-%m-%d")
        time_desc = "本月"
    else:
        date_start = "2026-07-01"
        date_end = "2026-07-31"
        time_desc = "最近"

    # 地点抽取（城市）
    location_candidates = re.findall(r'[\u4e00-\u9fa5]{2,}', query)
    location = "未知"
    if location_candidates:
        all_cities = list(CITY_NAME_TO_CODE.keys())
        # 简单匹配
        for candidate in location_candidates:
            if candidate in all_cities:
                location = candidate
                break

    # 概念抽取（业务概念，如"一线城市"、"字节跳动集团"）
    concept = "未知"
    concept_candidates = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z_]+', query)

    # 检测常见的概念模式
    if any(kw in query for kw in ["一线城市", "tier1", "Tier 1"]):
        concept = "tier1_cities"
    elif any(kw in query for kw in ["二线城市", "tier2", "Tier 2", "新一线"]):
        concept = "tier2_cities"
    elif any(kw in query for kw in ["华东区", "east_china"]):
        concept = "east_china"
    elif any(kw in query for kw in ["华中区", "central_china"]):
        concept = "central_china"
    elif any(kw in query for kw in ["字节跳动", "bytedance"]):
        concept = "bytedance_group"

    # 如果没有匹配到，尝试直接使用候选词
    if concept == "未知" and concept_candidates:
        concept = concept_candidates[0]

    # 指标抽取
    metric = "应收" if "应收" in query else "营收" if "营收" in query else "未知"

    return {
        "time": time_desc,
        "date_start": date_start,
        "date_end": date_end,
        "location": location,
        "concept": concept,
        "metric": metric
    }


@tool
def map_metric(metric_name: str) -> str:
    """
    步骤3：指标映射。
    将业务指标名映射为 SQL 聚合表达式。

    参数:
        metric_name: 业务指标名称（如"应收"、"营收"）

    返回:
        SQL聚合表达式（如"SUM(balance)"）
    """
    if metric_name in ["应收", "营收"]:
        return "SUM(balance)"
    else:
        return "SUM(balance)"


@tool
def map_dimension(dim_name: str) -> str:
    """
    步骤4：维度映射。
    将维度名映射为逻辑字段名。

    参数:
        dim_name: 维度名称（如"城市"）

    返回:
        逻辑字段名（如"city_name"）
    """
    if dim_name == "城市":
        return "city_name"
    elif dim_name == "客户":
        return "customer_id"
    else:
        return dim_name


@tool
def assemble_logical_sql(metric_expr: str, city_names: List[str], location: str,
                         date_start: str, date_end: str) -> str:
    """
    步骤5：组装逻辑 SQL。
    使用指标表达式、城市名称列表、地点和时间范围，生成逻辑 SQL。

    参数:
        metric_expr: SQL聚合表达式（如"SUM(balance)"）
        city_names: 城市名称列表（如["上海", "北京"]）
        location: 地点名称（用于日志）
        date_start: 开始日期
        date_end: 结束日期

    返回:
        逻辑SQL（包含业务名称）
    """
    if not city_names:
        return "错误：没有找到任何城市，无法生成SQL。"

    # 获取客户ID列表（将城市名称映射到客户ID）
    customer_ids = []
    for city in city_names:
        # 查找该城市的客户ID（假设城市名和客户名有对应关系）
        for entity_name, customer_id in ENTITY_TO_ID.items():
            if city in entity_name or CITY_CODE_TO_NAME.get(CITY_NAME_TO_CODE.get(city, ""), "") == city:
                customer_ids.append(customer_id)

    if not customer_ids:
        return f"错误：城市 {city_names} 没有对应的客户数据。"

    customer_in = ", ".join([f"'{cid}'" for cid in customer_ids])
    # 构建IN子句用于城市编码
    city_codes = [CITY_NAME_TO_CODE.get(city, "") for city in city_names if city in CITY_NAME_TO_CODE]
    city_codes = [code for code in city_codes if code]

    if city_codes:
        city_in = ", ".join([f"'{code}'" for code in city_codes])
        sql_template = f"""
        SELECT {metric_expr} AS total_balance
        FROM fact_account_receivable
        WHERE customer_id IN ({customer_in})
          AND city_code IN ({city_in})
          AND date BETWEEN '{date_start}' AND '{date_end}'
        """
    else:
        # 如果没有城市编码，仅使用客户ID
        sql_template = f"""
        SELECT {metric_expr} AS total_balance
        FROM fact_account_receivable
        WHERE customer_id IN ({customer_in})
          AND date BETWEEN '{date_start}' AND '{date_end}'
        """

    return sql_template.strip()


@tool
def execute_sql(sql: str) -> float:
    """
    步骤6：执行 SQL 并返回数值。

    参数:
        sql: 要执行的SQL语句

    返回:
        查询结果数值，或错误信息
    """
    conn = sqlite3.connect(FACT_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        result = row[0] if row else 0.0
    except Exception as e:
        result = f"SQL执行失败: {e}"
    finally:
        conn.close()
    return result


@tool
def validate_result(value: float, metric: str) -> bool:
    """
    步骤7：结果校验。
    利用业务规则检查结果是否合理。

    参数:
        value: 查询结果值
        metric: 指标名称

    返回:
        是否通过校验
    """
    if metric in ["应收", "营收"] and (isinstance(value, str) or value < 0):
        return False
    return True


# [AGC:END]

# ======================== 5. 导入本体扩层工具 ========================
from ontology.tools import logical_layer_expansion, set_global_model

# 设置全局模型
set_global_model(model)

# ======================== 6. 创建 Agent ========================
tools = [
    extract_entities_enhanced,
    logical_layer_expansion,  # 步骤2.2：本体逻辑扩层
    map_metric,
    map_dimension,
    assemble_logical_sql,
    execute_sql,
    validate_result
]

system_prompt = """你是一个 ChatBI 助手，专门查询企业应收款和营收数据。
你集成了新的本体逻辑扩层功能，支持多种业务概念的智能扩展。

请严格按照以下步骤执行：

步骤1：实体抽取
- 调用 extract_entities_enhanced 从用户输入中提取实体（时间、地点、概念、指标）
- 概念可以是抽象的，如"一线城市"、"字节跳动集团"、"华东区"等

步骤2：本体逻辑扩层（步骤3.3）
- 调用 logical_layer_expansion 进行概念扩层
- 将抽象概念扩展为具体的业务名称列表
- 参数说明：
  - concept_name: 抽象概念名称（支持别名，如"一线城市"、"tier1_cities"）
  - concept_category: 概念分类（city/customer/region/business），不指定则自动推断
  - return_type: 返回类型
    - "business_name": 返回业务名称列表（如["上海", "北京", "广州", "深圳"]）
    - "physical_code": 返回物理编码列表（如["021", "010", "020", "0755"]）
    - "both": 返回映射字典（如{"上海": "021", "北京": "010"}）

步骤3：指标映射
- 调用 map_metric 获取指标对应的 SQL 聚合表达式

步骤4：维度映射
- 调用 map_dimension 获取维度对应的逻辑字段名

步骤5：组装逻辑 SQL
- 调用 assemble_logical_sql 生成逻辑 SQL
- 传入扩层后的城市名称列表
- 注意：这里使用的是业务名称，后续会自动映射

步骤6：执行 SQL
- 调用 execute_sql 执行最终 SQL 并获取数值

步骤7：结果校验
- 调用 validate_result 校验结果是否合理

步骤8：返回答案
- 如果校验通过，给出自然语言答案，包含格式化金额
- 如果校验失败，提示用户数据异常

示例查询：
- "一线城市上个月应收多少" → 扩层为[上海,北京,广州,深圳]
- "华东区本月营收如何" → 扩层为[上海,杭州,南京,苏州]
- "字节跳动集团上个月应收" → 扩层为[上海分公司A, 北京分公司B, ...]

若某一步缺少必要参数，应主动向用户追问。
"""

agent = create_deep_agent(
    model=model,
    tools=tools,
    system_prompt=SystemMessage(content=system_prompt)
)


# ======================== 7. 测试函数 ========================
def test_ask_question(user_input: str):
    """测试Agent对话"""
    print(f"👤 用户: {user_input}\n")
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    # 提取最终回答
    final_message = result["messages"][-1]
    final_answer = final_message.content

    # 打印完整执行链路
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
#     # 测试用例
#     test_cases = [
#         "一线城市上个月应收多少",
#         "华东区本月营收如何",
#     ]
#
#     for question in test_cases:
#         print("\n" + "=" * 80)
#         test_ask_question(question)
#         print("\n")