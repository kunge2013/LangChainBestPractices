# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
ChatBI 工具函数集合

封装实体抽取、指标映射、SQL组装、执行和校验等工具。
"""

# [AGC:START] tool=Cc author=fangkun
import re
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict

from langchain_core.tools import tool


def create_chatbi_tools(
    entity_to_id: Dict[str, str],
    city_name_to_code: Dict[str, str],
    city_code_to_name: Dict[str, str],
    fact_db_path: str = "chatbi.db",
    concept_keyword_map: Dict[str, str] = None,
):
    """
    工厂函数：创建ChatBI工具列表。

    参数:
        entity_to_id: 业务名称 -> 客户ID
        city_name_to_code: 城市名称 -> 城市编码
        city_code_to_name: 城市编码 -> 城市名称
        fact_db_path: 事实数据库路径
        concept_keyword_map: 概念关键词映射 {keyword: display_name}

    返回:
        工具列表 [extract_entities_enhanced, map_metric, map_dimension, assemble_logical_sql, execute_sql, validate_result]
    """
    _concept_map = concept_keyword_map or {}

    @tool
    def extract_entities_enhanced(query: str) -> dict:
        """步骤1：增强型实体抽取。从用户查询中提取时间、地点、概念、指标。"""
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

        location_candidates = re.findall(r'[\u4e00-\u9fa5]{2,}', query)
        location = "未知"
        if location_candidates:
            all_cities = list(city_name_to_code.keys())
            for candidate in location_candidates:
                if candidate in all_cities:
                    location = candidate
                    break

        # 从本体字典动态匹配概念关键词
        concept = "未知"
        query_lower = query.lower()
        for keyword, display_name in _concept_map.items():
            kw_lower = keyword.lower()
            if kw_lower in query_lower:
                concept = display_name
                break

        if concept == "未知":
            concept_candidates = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z_]+', query)
            if concept_candidates:
                concept = concept_candidates[0]

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
        """步骤3：指标映射。将业务指标名映射为SQL聚合表达式。"""
        return "SUM(balance)"

    @tool
    def map_dimension(dim_name: str) -> str:
        """步骤4：维度映射。将维度名映射为逻辑字段名。"""
        if dim_name == "城市":
            return "city_name"
        elif dim_name == "客户":
            return "customer_id"
        return dim_name

    @tool
    def assemble_logical_sql(metric_expr: str, city_names: List[str], location: str,
                             date_start: str, date_end: str) -> str:
        """步骤5：组装逻辑SQL。使用指标表达式、城市名称列表和时间范围生成SQL。"""
        if not city_names:
            return "错误：没有找到任何城市，无法生成SQL。"

        customer_ids = []
        for city in city_names:
            for entity_name, customer_id in entity_to_id.items():
                if city in entity_name or city_code_to_name.get(city_name_to_code.get(city, ""), "") == city:
                    customer_ids.append(customer_id)

        if not customer_ids:
            return f"错误：城市 {city_names} 没有对应的客户数据。"

        customer_in = ", ".join([f"'{cid}'" for cid in customer_ids])
        city_codes = [city_name_to_code.get(city, "") for city in city_names if city in city_name_to_code]
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
            sql_template = f"""
            SELECT {metric_expr} AS total_balance
            FROM fact_account_receivable
            WHERE customer_id IN ({customer_in})
              AND date BETWEEN '{date_start}' AND '{date_end}'
            """

        return sql_template.strip()

    @tool
    def execute_sql(sql: str) -> float:
        """步骤6：执行SQL并返回数值。"""
        conn = sqlite3.connect(fact_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            row = cursor.fetchone()
            return row[0] if row else 0.0
        except Exception as e:
            return f"SQL执行失败: {e}"
        finally:
            conn.close()

    @tool
    def validate_result(value: float, metric: str) -> bool:
        """步骤7：结果校验。利用业务规则检查结果是否合理。"""
        if metric in ["应收", "营收"] and (isinstance(value, str) or value < 0):
            return False
        return True

    return [
        extract_entities_enhanced,
        map_metric,
        map_dimension,
        assemble_logical_sql,
        execute_sql,
        validate_result
    ]
# [AGC:END]
