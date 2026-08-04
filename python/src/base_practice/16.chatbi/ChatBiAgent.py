import os
import sqlite3
from datetime import datetime, timedelta

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# ======================== 1. 初始化 LLM ========================
model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "sk-xxx"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.0")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "1024")),
)

# ======================== 2. 初始化 SQLite 数据库 ========================
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
    sample_data = [
        ("CUST_WH_001", "420100", "2026-07-15", 18234500.00),
        ("CUST_WH_001", "420100", "2026-07-20", 12456700.00),
        ("CUST_WH_002", "420100", "2026-07-10", 12456700.00),
        ("CUST_WH_002", "420100", "2026-07-25", 9876500.00),
        ("CUST_WH_003", "420100", "2026-07-05", 3876600.00),
    ]
    cursor.executemany(
        "INSERT INTO fact_account_receivable (customer_id, city_code, date, balance) VALUES (?,?,?,?)",
        sample_data
    )
    conn.commit()
    conn.close()
    print("✅ SQLite 数据库初始化完成。")
initDb =os.environ.get("init_db", "True").lower() == 'true'
if initDb:
    init_db()

# ======================== 3. 业务映射与本体 ========================
ENTITY_TO_ID = {
    "武汉今日头条科技有限公司": "CUST_WH_001",
    "武汉抖音信息服务有限公司": "CUST_WH_002",
    "武汉飞书网络技术有限公司": "CUST_WH_003",
}
ID_TO_ENTITY = {v: k for k, v in ENTITY_TO_ID.items()}
CITY_CODE_MAP = {"武汉": "420100"}
ONTOLOGY = {
    "ByteDance_Group": {
        "subclasses": ["Wuhan_Douyin_Entity", "Wuhan_Toutiao_Entity", "Wuhan_Feishu_Entity"],
    },
    "Wuhan_Douyin_Entity": {"instances": ["CUST_WH_002"]},
    "Wuhan_Toutiao_Entity": {"instances": ["CUST_WH_001"]},
    "Wuhan_Feishu_Entity": {"instances": ["CUST_WH_003"]},
}

# ======================== 4. 定义工具（每个工具封装一个原子能力）=======================

@tool
def extract_entities(query: str) -> dict:
    """
    从用户自然语言问题中提取关键实体信息。
    返回一个包含 time, location, customer, metric 的字典。
    """
    # 这里用简单的启发式规则模拟，你可以替换为自己的 LLM 提取逻辑
    entities = {}
    if "上个月" in query:
        entities["time"] = "上个月"
    else:
        entities["time"] = "最近"

    if "武汉" in query:
        entities["location"] = "武汉"
    else:
        entities["location"] = "未知"

    if "字节跳动" in query or "头条" in query:
        entities["customer"] = "字节跳动"
    elif "抖音" in query:
        entities["customer"] = "抖音"
    elif "飞书" in query:
        entities["customer"] = "飞书"
    else:
        entities["customer"] = "未知"

    if "应收" in query:
        entities["metric"] = "应收"
    else:
        entities["metric"] = "未知"

    # 时间解析（固定示例）
    now = datetime(2026, 8, 4)
    if entities.get("time") == "上个月":
        first_day = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day = now.replace(day=1) - timedelta(days=1)
        date_range = (first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d"))
    else:
        date_range = ("2026-07-01", "2026-07-31")

    entities["date_start"] = date_range[0]
    entities["date_end"] = date_range[1]
    return entities


@tool
def expand_ontology(customer: str) -> list:
    """
    根据客户名称（如"字节跳动"）扩展出所有具体的公司实体名称列表。
    例如输入"字节跳动"会返回 ["武汉今日头条科技有限公司", "武汉抖音信息服务有限公司", "武汉飞书网络技术有限公司"]
    """
    if customer == "字节跳动":
        instances = []
        for cls in ONTOLOGY["ByteDance_Group"]["subclasses"]:
            instances.extend(ONTOLOGY[cls]["instances"])
        # 将ID转换为名称
        expanded = [ID_TO_ENTITY[i] for i in instances if i in ID_TO_ENTITY]
        return expanded
    else:
        # 支持单个客户名称
        for name, cid in ENTITY_TO_ID.items():
            if customer in name:
                return [name]
        return []


@tool
def generate_sql(metric: str, company_list: list, location: str, date_start: str, date_end: str) -> str:
    """
    根据指标、公司列表、地点和时间范围生成逻辑 SQL。
    返回 SQL 字符串。
    """
    if metric not in ["应收"]:
        metric = "应收"  # 仅演示
    metric_expr = "SUM(balance)"

    # 转义公司名称（防止 SQL 注入）
    escaped_companies = [f"'{c}'" for c in company_list]
    company_in = ", ".join(escaped_companies)
    logical_sql = f"""
    SELECT {metric_expr} AS total_ar
    FROM fact_account_receivable
    WHERE company_name IN ({company_in})
      AND city_name = '{location}'
      AND date BETWEEN '{date_start}' AND '{date_end}'
    """
    # 执行物理映射（将逻辑名称替换为物理字段和代码）
    sql = logical_sql
    for name, cid in ENTITY_TO_ID.items():
        sql = sql.replace(name, cid)
    if location in CITY_CODE_MAP:
        sql = sql.replace(location, CITY_CODE_MAP[location])
    sql = sql.replace("company_name", "customer_id").replace("city_name", "city_code")
    return sql.strip()


@tool
def execute_sql(sql: str) -> float:
    """
    执行 SQL 查询并返回数值结果。
    如果执行出错，返回错误信息（字符串）。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        result = row[0] if row else None
    except Exception as e:
        result = f"SQL执行失败: {e}"
    finally:
        conn.close()
    return result


# ======================== 5. 创建 Agent ========================
tools = [extract_entities, expand_ontology, generate_sql, execute_sql]

# 系统提示：告诉 Agent 如何合作使用这些工具
system_prompt = """你是一个 ChatBI 助手，专门回答企业应收款相关的查询。
请按照以下步骤回答用户问题：
1. 首先调用 extract_entities 提取用户问题中的关键信息（时间、地点、客户、指标）。
2. 然后调用 expand_ontology 将客户名称扩展为公司实体列表（如果是"字节跳动"则扩展到三家公司）。
3. 接着调用 generate_sql 生成 SQL 查询语句，需要传入指标、公司列表、地点、开始日期和结束日期。
4. 最后调用 execute_sql 执行 SQL 并得到数值。
5. 根据数值给出最终的自然语言回答，包含格式化金额。

如果用户的问题不够明确，你可以主动询问。
注意：所有的工具调用必须按顺序，不要跳过。
"""

agent = create_deep_agent(
    model=model,
    tools=tools,
    system_prompt=SystemMessage(content=system_prompt)
)


def test_ask_question():
    user_input = "上个月 武汉字节跳动应收多少"
    print(f"👤 用户: {user_input}\n")
    # 调用 Agent
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    # 提取最终回答
    final_message = result["messages"][-1]
    final_answer = final_message.content
    # 打印完整消息历史（用于追踪工具调用）
    print("=" * 60)
    print("🧠 完整执行链路追踪（工具调用顺序）")
    print("=" * 60)
    for msg in result["messages"]:
        if msg.type == "human":
            print(f"👤 用户: {msg.content}")
        elif msg.type == "ai":
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"🤖 调用工具: {tc['name']} 参数: {tc['args']}")
            else:
                print(f"🤖 最终回答: {msg.content}")
        elif msg.type == "tool":
            print(f"🔧 工具 {msg.name} 返回: {msg.content}")
    print("=" * 60)
    print(f"\n💬 最终回复: {final_answer}")


# ======================== 6. 运行示例 ========================
# test_ask_question()