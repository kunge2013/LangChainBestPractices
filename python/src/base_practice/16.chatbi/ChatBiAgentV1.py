import os
import re
import sqlite3
from datetime import datetime, timedelta
from difflib import get_close_matches
from typing import List, Dict, Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# ============================ 1. 初始化 LLM ============================
model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "sk-xxx"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.0")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "1024")),
)

# ============================ 2. 初始化 SQLite 数据库 ============================
DB_PATH = "chatbi.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    # 插入更多测试数据，覆盖不同公司
    sample_data = [
        ("CUST_WH_001", "420100", "2026-07-15", 18234500.00),
        ("CUST_WH_001", "420100", "2026-07-20", 12456700.00),
        ("CUST_WH_002", "420100", "2026-07-10", 12456700.00),
        ("CUST_WH_002", "420100", "2026-07-25", 9876500.00),
        ("CUST_WH_003", "420100", "2026-07-05", 3876600.00),
        ("CUST_WH_004", "420100", "2026-07-12", 5600000.00),   # 新增一家公司
    ]
    cursor.executemany(
        "INSERT INTO fact_account_receivable (customer_id, city_code, date, balance) VALUES (?,?,?,?)",
        sample_data
    )
    conn.commit()
    conn.close()
    print("✅ SQLite 数据库初始化完成。")

if os.environ.get("init_db", "True").lower() == 'true':
    init_db()

# ============================ 3. 元数据存储（替代硬编码） ============================
# 3.1 实体字典（用于实体消歧和模糊匹配）
ENTITY_DICT = {
    "武汉": {"type": "city", "name": "武汉", "aliases": ["江城", "WH", "wuhan"]},
    "字节跳动": {"type": "company_group", "name": "字节跳动", "aliases": ["bytedance", "头条", "Bytedance"]},
    "抖音": {"type": "company", "name": "抖音", "aliases": ["douyin", "抖音信息服务"]},
    "飞书": {"type": "company", "name": "飞书", "aliases": ["feishu", "飞书网络"]},
    "今日头条": {"type": "company", "name": "今日头条", "aliases": ["toutiao", "头条科技"]},
}

# 3.2 物理映射表（城市名称 → 编码）
CITY_CODE_MAP = {"武汉": "420100"}

# 3.3 客户名称 → 客户ID映射
ENTITY_TO_ID = {
    "武汉今日头条科技有限公司": "CUST_WH_001",
    "武汉抖音信息服务有限公司": "CUST_WH_002",
    "武汉飞书网络技术有限公司": "CUST_WH_003",
    "武汉斗鱼网络科技有限公司": "CUST_WH_004",   # 新增示例
}
ID_TO_ENTITY = {v: k for k, v in ENTITY_TO_ID.items()}

# 3.4 本体（图结构，支持子类/组扩展）
ONTOLOGY = {
    "ByteDance_Group": {
        "type": "Group",
        "subClassOf": None,
        "members": ["CUST_WH_001", "CUST_WH_002", "CUST_WH_003"]
    },
    "Wuhan_Subsidiaries": {
        "type": "Group",
        "subClassOf": "ByteDance_Group",
        "members": ["CUST_WH_001", "CUST_WH_002", "CUST_WH_003"]
    }
}

# ============================ 4. 工具函数（每个工具封装一个原子能力） ============================

@tool
def extract_entities_enhanced(query: str) -> dict:
    """
    步骤1：增强型实体抽取。
    结合 LLM（此处用规则模拟） + 实体字典 + 模糊匹配，提取时间、地点、客户、指标。
    返回结构化的实体字典。
    """
    # ---- 4.1 时间抽取 ----
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
        # 默认最近一个月（2026-07）
        date_start = "2026-07-01"
        date_end = "2026-07-31"
        time_desc = "最近"

    # ---- 4.2 地点抽取 + 模糊匹配 ----
    # 提取所有中文词汇作为候选
    location_candidates = re.findall(r'[\u4e00-\u9fa5]{2,}', query)
    location = "未知"
    if location_candidates:
        # 获取所有城市名称
        all_cities = [item["name"] for item in ENTITY_DICT.values() if item.get("type") == "city"]
        # 取第一个候选词进行模糊匹配
        match = get_close_matches(location_candidates[0], all_cities, n=1, cutoff=0.5)
        if match:
            location = match[0]

    # ---- 4.3 客户抽取 ----
    customer = "未知"
    # 优先识别组名（如"字节跳动"）
    group_keywords = ["字节跳动", "头条", "bytedance"]
    for kw in group_keywords:
        if kw.lower() in query.lower():
            customer = "字节跳动"
            break
    else:
        # 识别单个公司
        company_keywords = ["抖音", "飞书", "斗鱼"]
        for kw in company_keywords:
            if kw in query:
                customer = kw
                break
    # 如果仍然未知，尝试从实体字典反向匹配
    if customer == "未知":
        for key, info in ENTITY_DICT.items():
            if info.get("type") in ["company", "company_group"]:
                for alias in info["aliases"]:
                    if alias in query:
                        customer = info["name"]
                        break
                if customer != "未知":
                    break

    # ---- 4.4 指标抽取 ----
    metric = "应收" if "应收" in query else "未知"

    return {
        "time": time_desc,
        "date_start": date_start,
        "date_end": date_end,
        "location": location,
        "customer": customer,
        "metric": metric
    }


@tool
def expand_ontology(concept: str) -> list:
    """
    步骤2：本体推理。
    输入业务概念（如"字节跳动"、"武汉子公司"），返回具体的客户 ID 列表。
    支持组扩展和子类继承。
    """
    # 如果概念是"字节跳动"或"头条"，返回组内所有成员 ID
    if concept in ["字节跳动", "头条", "bytedance"]:
        return ONTOLOGY["ByteDance_Group"]["members"]
    elif concept == "武汉子公司":
        return ONTOLOGY["Wuhan_Subsidiaries"]["members"]
    else:
        # 尝试匹配单个客户名称
        for name, cid in ENTITY_TO_ID.items():
            if concept in name or name in concept:
                return [cid]
        # 如果都没匹配到，返回空列表
        return []


@tool
def map_metric(metric_name: str) -> str:
    """
    步骤3：指标映射。
    将业务指标名映射为 SQL 聚合表达式。
    """
    if metric_name == "应收":
        return "SUM(balance)"
    else:
        # 默认
        return "SUM(balance)"


@tool
def map_dimension(dim_name: str) -> str:
    """
    步骤4：维度映射。
    将维度名（如"城市"）映射为逻辑字段名（用于后续物理替换）。
    """
    if dim_name == "城市":
        return "city_name"
    elif dim_name == "客户":
        return "customer_id"
    else:
        return dim_name


@tool
def assemble_logical_sql(metric_expr: str, dim_fields: dict, company_ids: list,
                         location: str, date_start: str, date_end: str) -> str:
    """
    步骤5：组装逻辑 SQL。
    使用映射后的指标表达式、维度逻辑字段、客户ID列表、地点和时间范围，
    生成带有业务名称（如'武汉'）的逻辑 SQL。
    """
    if not company_ids:
        return "错误：没有找到任何客户，无法生成SQL。"
    company_in = ", ".join([f"'{cid}'" for cid in company_ids])
    # 注意：这里 city_name = '武汉' 是逻辑名，后续会被物理替换
    sql_template = f"""
    SELECT {metric_expr} AS total_ar
    FROM fact_account_receivable
    WHERE customer_id IN ({company_in})
      AND city_name = '{location}'
      AND date BETWEEN '{date_start}' AND '{date_end}'
    """
    return sql_template.strip()


@tool
def map_physical_values(logical_sql: str, location: str) -> str:
    """
    步骤6：物理值映射。
    将逻辑 SQL 中的业务名称替换为物理存储的编码和字段名。
    例如：city_name → city_code, '武汉' → '420100'
    """
    sql = logical_sql
    # 替换地点名称 → 城市编码（注意处理引号）
    if location in CITY_CODE_MAP:
        code = CITY_CODE_MAP[location]
        # 替换单引号内的文本，确保准确
        sql = sql.replace(f"'{location}'", f"'{code}'")
    # 字段名映射
    sql = sql.replace("city_name", "city_code")
    return sql


@tool
def execute_sql(sql: str) -> float:
    """
    步骤7：执行 SQL 并返回数值。
    如果出错，返回错误信息（字符串）。
    """
    conn = sqlite3.connect(DB_PATH)
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
    步骤8：结果校验。
    利用业务规则（本体中定义的约束）检查结果是否合理。
    """
    if metric == "应收" and value < 0:
        return False
    # 可以增加其他规则，例如金额上限等
    return True


# ============================ 5. 创建 Agent ============================
tools = [
    extract_entities_enhanced,
    expand_ontology,
    map_metric,
    map_dimension,
    assemble_logical_sql,
    map_physical_values,
    execute_sql,
    validate_result
]

system_prompt = """你是一个 ChatBI 助手，专门查询企业应收款数据。
请严格按照以下步骤执行，每一步必须按顺序调用工具，不得跳过：

1. 调用 extract_entities_enhanced 从用户输入中提取实体（时间、地点、客户、指标）。
2. 调用 expand_ontology 将客户概念（如“字节跳动”）扩展为具体的客户 ID 列表。
3. 调用 map_metric 获取指标对应的 SQL 聚合表达式。
4. 调用 map_dimension 获取维度对应的逻辑字段名（如“城市” → “city_name”）。
5. 调用 assemble_logical_sql 生成带业务名的逻辑 SQL，需要传入 metric_expr、dim_fields、company_ids、location、date_start、date_end。
   注意：dim_fields 可以从上一步结果中构建，例如 {"city": map_dimension("城市")}，实际使用中，你可以将维度映射结果组装成字典。
   如果缺少，可以直接传入空字典，但 city 维度必须提供。
6. 调用 map_physical_values 将逻辑 SQL 中的业务名（如‘武汉’）替换为物理编码（如‘420100’）和物理字段（city_code）。
7. 调用 execute_sql 执行最终 SQL 并获取数值。
8. 调用 validate_result 校验结果是否合理（如应收款不能为负数）。
9. 如果校验通过，给出自然语言答案，包含格式化金额；如果校验失败，提示用户数据异常。

若某一步缺少必要参数，应主动向用户追问。
注意：dim_fields 参数在 assemble_logical_sql 中需要传入一个字典，例如 {"city": "city_name"}，你可以从前面 map_dimension 的结果构建。
"""

agent = create_deep_agent(
    model=model,
    tools=tools,
    system_prompt=SystemMessage(content=system_prompt)
)


# ============================ 6. 测试函数 ============================
def test_ask_question():
    user_input = "上个月 武汉字节跳动应收多少"
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


if __name__ == "__main__":
    test_ask_question()