import os
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import TypedDict, Optional, List, Dict, Any

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

# 尝试导入 DeepAgent 中间件（若未安装，可先 pip install deepagents）
try:
    from deepagents.middleware.filesystem import FilesystemMiddleware
    from langgraph.graph import MessagesState
    HAS_DEEPAGENT = True
except ImportError:
    HAS_DEEPAGENT = False
    print("⚠️ deepagents 未安装，将跳过中间件增强。")

# ======================== 1. 初始化 LLM ========================
model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "sk-xxx"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.0")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "1024")),
)

# ======================== 2. 初始化 SQLite 数据库 ========================
DB_PATH = "chabi/chatbi.db"

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

# ======================== 4. 状态定义（全流程追踪）=======================
class ChatBIState(TypedDict):
    user_input: str
    # 阶段1输出
    entities: Optional[Dict[str, str]]
    intent: Optional[str]
    slots: Optional[Dict[str, Any]]
    # 阶段2输出
    linked_classes: Optional[List[str]]
    expanded_instances: Optional[List[str]]
    # 阶段3输出
    logical_sql: Optional[str]
    # 阶段4输出
    physical_sql_mid: Optional[str]
    # 阶段5输出
    final_sql: Optional[str]
    raw_result: Optional[Any]
    # 阶段6输出
    validation_passed: Optional[bool]
    formatted_result: Optional[str]
    final_response: Optional[str]
    error: Optional[str]
    retry_count: int

# ======================== 5. 节点函数（每个阶段一个节点）=======================

# ---------- 阶段2：NLU ----------
ENTITY_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content="提取时间、地点、客户、指标。输出JSON。"),
    HumanMessage(content="{user_input}")
])

def nlu_node(state: ChatBIState) -> ChatBIState:
    chain = ENTITY_PROMPT | model | JsonOutputParser()
    try:
        entities = chain.invoke({"user_input": state["user_input"]})
    except:
        entities = {"time": "上个月", "location": "武汉", "customer": "字节跳动", "metric": "应收"}

    # 时间解析
    now = datetime(2026, 8, 4)
    if entities.get("time") == "上个月":
        first_day = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day = now.replace(day=1) - timedelta(days=1)
        date_range = (first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d"))
    else:
        date_range = ("2026-07-01", "2026-07-31")

    state["entities"] = entities
    state["intent"] = "METRIC_QUERY"
    state["slots"] = {
        "metric": entities.get("metric", "应收"),
        "location": entities.get("location", "武汉"),
        "customer": entities.get("customer", "字节跳动"),
        "date_start": date_range[0],
        "date_end": date_range[1],
    }
    return state

# ---------- 阶段3：本体推理 ----------
def ontology_node(state: ChatBIState) -> ChatBIState:
    customer = state["slots"]["customer"]
    linked = ["ByteDance_Group"] if customer == "字节跳动" else []
    instances = []
    for cls in ONTOLOGY["ByteDance_Group"]["subclasses"]:
        instances.extend(ONTOLOGY[cls]["instances"])
    expanded = [ID_TO_ENTITY[i] for i in instances if i in ID_TO_ENTITY]
    state["linked_classes"] = linked
    state["expanded_instances"] = expanded
    return state

# ---------- 阶段4：语义映射 ----------
def semantic_node(state: ChatBIState) -> ChatBIState:
    slots = state["slots"]
    metric = slots["metric"]
    metric_expr = "SUM(balance)" if metric == "应收" else "SUM(balance)"
    company_list = "', '".join(state["expanded_instances"])
    logical_sql = f"""
    SELECT {metric_expr} AS total_ar
    FROM fact_account_receivable
    WHERE company_name IN ('{company_list}')
      AND city_name = '{slots["location"]}'
      AND date BETWEEN '{slots["date_start"]}' AND '{slots["date_end"]}'
    """
    state["logical_sql"] = logical_sql.strip()
    return state

# ---------- 阶段5：物理值映射 ----------
def physical_mapping_node(state: ChatBIState) -> ChatBIState:
    sql = state["logical_sql"]
    for name, cid in ENTITY_TO_ID.items():
        sql = sql.replace(name, cid)
    city = state["slots"]["location"]
    if city in CITY_CODE_MAP:
        sql = sql.replace(city, CITY_CODE_MAP[city])
    physical_sql = sql.replace("company_name", "customer_id").replace("city_name", "city_code")
    state["physical_sql_mid"] = physical_sql
    return state

# ---------- 阶段6：编译与执行 ----------
def compile_execute_node(state: ChatBIState) -> ChatBIState:
    final_sql = state["physical_sql_mid"]  # SQLite 兼容
    state["final_sql"] = final_sql
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(final_sql)
        row = cursor.fetchone()
        result = row[0] if row else None
    except Exception as e:
        state["error"] = f"SQL执行失败: {e}"
        result = None
    finally:
        conn.close()
    state["raw_result"] = result
    return state

# ---------- 阶段7：校验 ----------
def validation_node(state: ChatBIState) -> ChatBIState:
    raw = state["raw_result"]
    if raw is not None and raw >= 0 and raw < 100000000:
        state["validation_passed"] = True
    else:
        state["validation_passed"] = False
        state["error"] = f"结果异常：{raw}"
    return state

# ---------- 阶段7：格式化输出 ----------
def format_response_node(state: ChatBIState) -> ChatBIState:
    raw = state["raw_result"]
    formatted = f"{raw:,.2f} 元" if raw is not None else "无数据"
    state["formatted_result"] = formatted
    state["final_response"] = (
        f"✅ 查询完成！{state['slots']['location']}{state['slots']['customer']}"
        f"上个月{state['slots']['metric']}总额为 **{formatted}** 。"
    )
    return state

# ---------- 错误处理 ----------
def error_node(state: ChatBIState) -> ChatBIState:
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["final_response"] = f"❌ 查询失败：{state.get('error', '未知错误')}"
    return state

# ======================== 6. 构建图（流程清晰可见）=======================
def build_graph():
    graph = StateGraph(ChatBIState)

    # 添加节点（7个阶段 + 1个错误）
    graph.add_node("nlu", nlu_node)
    graph.add_node("ontology", ontology_node)
    graph.add_node("semantic", semantic_node)
    graph.add_node("physical_mapping", physical_mapping_node)
    graph.add_node("compile_execute", compile_execute_node)
    graph.add_node("validate", validation_node)
    graph.add_node("format", format_response_node)
    graph.add_node("error", error_node)

    # 设置入口
    graph.set_entry_point("nlu")

    # 顺序执行（流水线）
    graph.add_edge("nlu", "ontology")
    graph.add_edge("ontology", "semantic")
    graph.add_edge("semantic", "physical_mapping")
    graph.add_edge("physical_mapping", "compile_execute")
    graph.add_edge("compile_execute", "validate")

    # 条件路由（校验通过 -> 格式化，否则 -> 错误）
    def route_after_validate(state: ChatBIState) -> str:
        return "format" if state.get("validation_passed") else "error"

    graph.add_conditional_edges("validate", route_after_validate, {
        "format": "format",
        "error": "error"
    })
    graph.add_edge("format", END)
    graph.add_edge("error", END)

    return graph.compile()

# ======================== 7. 运行主程序 ========================
if __name__ == "__main__":
    # 如果需要启用 DeepAgent 文件系统中间件增强（可选）
    # 这里仅演示标准 LangGraph 显式流程
    app = build_graph()

    initial_state = {
        "user_input": "上个月 武汉字节跳动应收多少",
        "entities": None, "intent": None, "slots": None,
        "linked_classes": None, "expanded_instances": None,
        "logical_sql": None, "physical_sql_mid": None, "final_sql": None,
        "raw_result": None, "validation_passed": None,
        "formatted_result": None, "final_response": None,
        "error": None, "retry_count": 0,
    }

    result = app.invoke(initial_state)

    # 打印完整追踪（展示每个阶段的数据流）
    print("\n" + "=" * 60)
    print("🧠 完整执行链路追踪（每个阶段的输入/输出）")
    print("=" * 60)
    print(f"📥 用户输入: {result['user_input']}")
    print(f"📌 阶段2 (NLU) 槽位: {result['slots']}")
    print(f"📌 阶段3 (本体) 扩层实例: {result['expanded_instances']}")
    print(f"📌 阶段4 (语义) 逻辑SQL:\n{result['logical_sql']}")
    print(f"📌 阶段5 (物理映射) 中间态SQL:\n{result['physical_sql_mid']}")
    print(f"📌 阶段6 (编译执行) 最终SQL:\n{result['final_sql']}")
    print(f"📌 阶段6 (执行) 原始结果: {result['raw_result']}")
    print(f"📌 阶段7 (校验) 是否通过: {result['validation_passed']}")
    print("\n" + "=" * 60)
    print(f"💬 最终回复: {result['final_response']}")
    print("=" * 60)