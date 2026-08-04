import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from difflib import get_close_matches
import re

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
    temperature=0.0,
)

# ============================ 2. 初始化数据库（含维度表） ============================
DB_PATH = "chatbi_mut_metric.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 事实表（包含多个指标字段）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            city_code TEXT NOT NULL,
            date TEXT NOT NULL,
            revenue REAL NOT NULL,
            profit REAL NOT NULL,
            order_id TEXT NOT NULL
        )
    ''')
    # 维度表：客户
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL
        )
    ''')
    # 维度表：产品
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_product (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL
        )
    ''')
    # 维度表：账户（注意：账户名可能与客户名相同，但它们是不同维度）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_account (
            account_id TEXT PRIMARY KEY,
            account_name TEXT NOT NULL
        )
    ''')
    # 维度表：城市
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_city (
            city_code TEXT PRIMARY KEY,
            city_name TEXT NOT NULL
        )
    ''')

    # 清空并插入测试数据
    cursor.execute("DELETE FROM fact_sales")
    cursor.execute("DELETE FROM dim_customer")
    cursor.execute("DELETE FROM dim_product")
    cursor.execute("DELETE FROM dim_account")
    cursor.execute("DELETE FROM dim_city")

    # 客户维度
    customers = [
        ("CUST_001", "武汉今日头条科技有限公司"),
        ("CUST_002", "武汉抖音信息服务有限公司"),
        ("CUST_003", "武汉飞书网络技术有限公司"),
        ("CUST_004", "武汉斗鱼网络科技有限公司"),
    ]
    cursor.executemany("INSERT INTO dim_customer VALUES (?,?)", customers)

    # 产品维度
    products = [
        ("PROD_001", "广告服务"),
        ("PROD_002", "云存储"),
        ("PROD_003", "企业协作"),
    ]
    cursor.executemany("INSERT INTO dim_product VALUES (?,?)", products)

    # 账户维度（注意账户名与客户名可能重复，如“字节跳动”既是客户名也是账户名）
    accounts = [
        ("ACC_001", "字节跳动"),
        ("ACC_002", "腾讯"),
        ("ACC_003", "阿里"),
    ]
    cursor.executemany("INSERT INTO dim_account VALUES (?,?)", accounts)

    # 城市维度
    cities = [
        ("420100", "武汉"),
        ("110000", "北京"),
        ("310000", "上海"),
    ]
    cursor.executemany("INSERT INTO dim_city VALUES (?,?)", cities)

    # 事实表数据：包含多个指标
    facts = [
        ("CUST_001", "PROD_001", "ACC_001", "420100", "2026-07-15", 18234500.0, 3200000.0, "ORD001"),
        ("CUST_001", "PROD_002", "ACC_001", "420100", "2026-07-20", 12456700.0, 2100000.0, "ORD002"),
        ("CUST_002", "PROD_001", "ACC_001", "420100", "2026-07-10", 12456700.0, 1500000.0, "ORD003"),
        ("CUST_002", "PROD_003", "ACC_002", "420100", "2026-07-25", 9876500.0, 1200000.0, "ORD004"),
        ("CUST_003", "PROD_002", "ACC_001", "420100", "2026-07-05", 3876600.0, 600000.0, "ORD005"),
        ("CUST_004", "PROD_003", "ACC_003", "420100", "2026-07-12", 5600000.0, 800000.0, "ORD006"),
    ]
    cursor.executemany(
        "INSERT INTO fact_sales (customer_id, product_id, account_id, city_code, date, revenue, profit, order_id) VALUES (?,?,?,?,?,?,?,?)",
        facts
    )
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成（含维度表）。")

if os.environ.get("init_db", "True").lower() == 'true':
    init_db()

# ============================ 3. 加载元数据配置 ============================
# 这里使用字典模拟配置文件，实际可从JSON/YAML文件读取
METRICS_CONFIG = {
    "营收": {"expression": "SUM(revenue)", "agg_type": "SUM", "field": "revenue"},
    "利润": {"expression": "SUM(profit)", "agg_type": "SUM", "field": "profit"},
    "订单量": {"expression": "COUNT(DISTINCT order_id)", "agg_type": "COUNT_DISTINCT", "field": "order_id"},
}
DIMENSIONS_CONFIG = {
    "客户": {
        "logical_field": "customer_name",
        "physical_field": "customer_id",
        "mapping_table": "dim_customer",
        "key_field": "customer_id",
        "value_field": "customer_name",
        "aliases": ["顾客", "买方"]
    },
    "产品": {
        "logical_field": "product_name",
        "physical_field": "product_id",
        "mapping_table": "dim_product",
        "key_field": "product_id",
        "value_field": "product_name",
        "aliases": ["商品", "SKU"]
    },
    "账户": {
        "logical_field": "account_name",
        "physical_field": "account_id",
        "mapping_table": "dim_account",
        "key_field": "account_id",
        "value_field": "account_name",
        "aliases": ["账号", "户名"]
    },
    "城市": {
        "logical_field": "city_name",
        "physical_field": "city_code",
        "mapping_table": "dim_city",
        "key_field": "city_code",
        "value_field": "city_name",
        "aliases": ["地区"]
    }
}
# 本体配置
ONTOLOGY = {
    "groups": {
        "字节跳动": {
            "members": ["CUST_001", "CUST_002", "CUST_003"]
        },
        "腾讯": {
            "members": ["CUST_004"]  # 假设
        }
    },
    "rules": {
        "profit_non_negative": "profit >= 0",
        "revenue_positive": "revenue > 0"
    }
}
# 物理映射表（这里仅示例，实际应查询数据库）
# 城市编码映射
CITY_CODE_MAP = {"武汉": "420100", "北京": "110000", "上海": "310000"}
# 客户名称→ID（用于快速映射）
CUSTOMER_NAME_TO_ID = {
    "武汉今日头条科技有限公司": "CUST_001",
    "武汉抖音信息服务有限公司": "CUST_002",
    "武汉飞书网络技术有限公司": "CUST_003",
    "武汉斗鱼网络科技有限公司": "CUST_004",
}
# 产品名称→ID
PRODUCT_NAME_TO_ID = {
    "广告服务": "PROD_001",
    "云存储": "PROD_002",
    "企业协作": "PROD_003",
}
# 账户名称→ID
ACCOUNT_NAME_TO_ID = {
    "字节跳动": "ACC_001",
    "腾讯": "ACC_002",
    "阿里": "ACC_003",
}

# ============================ 4. 工具函数（通用） ============================

@tool
def extract_entities_universal(query: str) -> dict:
    """
    步骤1：抽取多指标、多维度实体。
    返回包含 time, location, customer_group, metrics (list), dimensions (list) 等。
    """
    now = datetime(2026, 8, 4)
    # 时间解析
    if "上个月" in query:
        first_day = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day = now.replace(day=1) - timedelta(days=1)
        date_start = first_day.strftime("%Y-%m-%d")
        date_end = last_day.strftime("%Y-%m-%d")
        time_desc = "上个月"
    else:
        date_start = "2026-07-01"
        date_end = "2026-07-31"
        time_desc = "最近"

    # 地点抽取（模糊匹配）
    location = "武汉"  # 默认，可增强
    # 客户组抽取
    customer_group = None
    for group in ONTOLOGY["groups"].keys():
        if group in query:
            customer_group = group
            break
    # 指标抽取：从配置中匹配
    metrics = []
    for mname in METRICS_CONFIG.keys():
        if mname in query:
            metrics.append(mname)
    if not metrics:
        metrics = ["营收"]  # 默认

    # 维度抽取
    dimensions = []
    for dname, dinfo in DIMENSIONS_CONFIG.items():
        if dname in query or any(alias in query for alias in dinfo.get("aliases", [])):
            dimensions.append(dname)
    if not dimensions:
        dimensions = ["客户"]  # 默认

    return {
        "time": time_desc,
        "date_start": date_start,
        "date_end": date_end,
        "location": location,
        "customer_group": customer_group,
        "metrics": metrics,
        "dimensions": dimensions
    }


@tool
def expand_ontology_universal(group_name: str) -> list:
    """步骤2：本体扩层，返回客户ID列表"""
    if group_name in ONTOLOGY["groups"]:
        return ONTOLOGY["groups"][group_name]["members"]
    else:
        # 尝试单个客户名
        for name, cid in CUSTOMER_NAME_TO_ID.items():
            if group_name in name or name in group_name:
                return [cid]
        return []


@tool
def map_metrics(metric_names: list) -> str:
    """步骤3：将指标列表映射为 SQL 选择列表（逗号分隔）"""
    exprs = []
    for m in metric_names:
        if m in METRICS_CONFIG:
            exprs.append(f"{METRICS_CONFIG[m]['expression']} AS {m}")
        else:
            exprs.append(f"SUM(1) AS unknown")  # fallback
    return ", ".join(exprs)


@tool
def map_dimensions(dim_names: list) -> dict:
    """
    步骤4：将维度列表映射为逻辑字段名（返回字典：维度名 → 逻辑字段名）
    并标记哪些维度字段可能取值相同（需歧义消解）
    """
    dim_map = {}
    for d in dim_names:
        if d in DIMENSIONS_CONFIG:
            dim_map[d] = DIMENSIONS_CONFIG[d]["logical_field"]
        else:
            dim_map[d] = d
    return dim_map


@tool
def resolve_ambiguity(dim_names: list, query: str) -> dict:
    """
    步骤5：歧义消解。
    如果查询中同时出现'账户'和'客户'，且它们的逻辑字段可能同名（但物理字段不同），
    通过语义层明确区分。
    返回维度到物理字段的映射。
    """
    # 在此处，我们根据配置明确每个维度对应的物理字段
    physical_fields = {}
    for d in dim_names:
        if d in DIMENSIONS_CONFIG:
            physical_fields[d] = DIMENSIONS_CONFIG[d]["physical_field"]
    return physical_fields


@tool
def assemble_logical_sql(metric_expr: str, dim_fields: dict,
                         customer_ids: list, location: str,
                         date_start: str, date_end: str) -> str:
    """
    步骤6：组装逻辑SQL（带业务名称）
    """
    if not customer_ids:
        return "错误：没有找到任何客户。"
    customer_in = ", ".join([f"'{cid}'" for cid in customer_ids])
    # 构建 SELECT 子句：指标表达式 + 维度字段（逻辑名）
    select_items = [metric_expr]
    for dim, field in dim_fields.items():
        select_items.append(field)
    select_clause = ", ".join(select_items)

    # WHERE 条件
    where = f"customer_id IN ({customer_in}) AND city_name = '{location}' AND date BETWEEN '{date_start}' AND '{date_end}'"
    # GROUP BY 维度（如果有多个维度）
    group_by = ""
    if len(dim_fields) > 0:
        group_by = "GROUP BY " + ", ".join(dim_fields.values())

    sql = f"""
    SELECT {select_clause}
    FROM fact_sales
    WHERE {where}
    {group_by}
    """
    return sql.strip()


@tool
def map_physical_values(logical_sql: str, dim_physical_map: dict, location: str) -> str:
    """
    步骤7：物理值映射，替换所有业务名称为编码。
    包括城市、客户、产品、账户等。
    """
    sql = logical_sql
    # 替换城市名称
    if location in CITY_CODE_MAP:
        sql = sql.replace(f"'{location}'", f"'{CITY_CODE_MAP[location]}'")
    # 替换维度字段名（逻辑→物理）
    for dim, phys_field in dim_physical_map.items():
        logical_field = DIMENSIONS_CONFIG.get(dim, {}).get("logical_field", dim)
        sql = sql.replace(logical_field, phys_field)
    # 额外处理：客户ID已经物理，无需替换
    return sql


@tool
def execute_sql(sql: str) -> List[Dict[str, Any]]:
    """
    步骤8：执行SQL，返回结果集（列表字典）
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
    except Exception as e:
        result = [{"error": f"SQL执行失败: {e}"}]
    finally:
        conn.close()
    return result


@tool
def validate_results(results: List[Dict], metrics: list) -> bool:
    """
    步骤9：根据本体规则校验结果
    """
    for row in results:
        # 检查利润非负
        if "利润" in row and row["利润"] < 0:
            return False
        if "营收" in row and row["营收"] < 0:
            return False
    return True


@tool
def format_results(results: List[Dict], metrics: list, dimensions: list) -> str:
    """
    步骤10：将结果格式化为自然语言 + 表格
    """
    if not results:
        return "未查询到数据。"
    # 生成简单文本描述
    summary = f"查询结果共 {len(results)} 条记录。\n"
    # 构建表格（Markdown风格）
    headers = metrics + dimensions
    table = "| " + " | ".join(headers) + " |\n"
    table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in results:
        row_str = []
        for h in headers:
            row_str.append(str(row.get(h, "")))
        table += "| " + " | ".join(row_str) + " |\n"
    return summary + table


# ============================ 5. 创建 Agent ============================
tools = [
    extract_entities_universal,
    expand_ontology_universal,
    map_metrics,
    map_dimensions,
    resolve_ambiguity,
    assemble_logical_sql,
    map_physical_values,
    execute_sql,
    validate_results,
    format_results
]

system_prompt = """你是一个通用 ChatBI 助手，支持多指标、多维度查询。
请严格按照以下步骤执行：

1. 调用 extract_entities_universal 抽取所有实体（时间、地点、客户组、指标列表、维度列表）。
2. 调用 expand_ontology_universal 将客户组扩展为客户ID列表。
3. 调用 map_metrics 将指标列表转换为 SQL 选择表达式。
4. 调用 map_dimensions 将维度列表映射为逻辑字段名（返回字典）。
5. 调用 resolve_ambiguity 处理可能存在的维度歧义（如账户和客户同名），返回物理字段映射。
6. 调用 assemble_logical_sql 生成逻辑 SQL，需要传入 metric_expr（步骤3的结果）、dim_fields（步骤4的结果）、customer_ids、location、date_start、date_end。
7. 调用 map_physical_values 将逻辑 SQL 中的业务名替换为物理编码，需要传入 dim_physical_map（步骤5的结果）和 location。
8. 调用 execute_sql 执行 SQL 并获取结果集（列表字典）。
9. 调用 validate_results 校验结果是否合理。
10. 调用 format_results 将结果格式化为自然语言和表格输出。

如果任何步骤缺少必要信息，应主动询问用户。
"""

agent = create_deep_agent(
    model=model,
    tools=tools,
    system_prompt=SystemMessage(content=system_prompt)
)


def test_query():
    user_input = "上个月武汉字节跳动的营收和利润，按客户和产品看"
    print(f"👤 用户: {user_input}\n")
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    final_answer = result["messages"][-1].content
    print("=" * 60)
    print("🧠 执行链路追踪")
    for msg in result["messages"]:
        if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"🤖 调用工具: {tc['name']} 参数: {tc['args']}")
        elif msg.type == "tool":
            print(f"🔧 工具 {msg.name} 返回: {msg.content[:100]}...")
    print("=" * 60)
    print(f"💬 最终回复:\n{final_answer}")

# if __name__ == "__main__":
#     test_query()