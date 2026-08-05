# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
本体查询引擎：基于递归CTE实现多级扩层查询
"""

# [AGC:START] tool=Cc author=fangkun
import sqlite3
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class OntologyQueryEngine:
    """
    本体查询引擎

    封装递归CTE查询逻辑，支持多级扩层查询
    """

    class ConceptNotFoundError(Exception):
        """概念未找到异常"""
        pass

    def __init__(self, db_path: str):
        """
        初始化查询引擎

        参数:
            db_path: SQLite数据库路径
        """
        self.db_path = db_path

    def expand_concept(
        self,
        concept_name: str,
        max_level: int = None,
        return_type: str = "business_name"
    ) -> List[str] | Dict[str, str]:
        """
        扩层查询：给定概念名称，返回所有下级实例列表

        参数:
            concept_name: 概念名称
            max_level: 最大扩层深度（None表示不限）
            return_type: 返回类型
                - "business_name": 业务名称
                - "physical_code": 物理编码
                - "both": 返回字典 {"business_name": "physical_code"}

        返回:
            实例列表或字典列表

        异常:
            ConceptNotFoundError: 概念未找到
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 验证概念是否存在
            cursor.execute(
                "SELECT id, concept_category FROM ontology_nodes WHERE node_name = ?",
                (concept_name,)
            )
            concept_row = cursor.fetchone()
            if not concept_row:
                raise self.ConceptNotFoundError(f"概念 '{concept_name}' 未在数据库中找到")

            # 验证 max_level 参数安全
            if max_level is not None:
                if not isinstance(max_level, int) or max_level <= 0:
                    raise ValueError(f"max_level 必须是正整数，当前值: {max_level}")

            # 构建递归CTE查询
            level_filter = f"AND expand.level <= {max_level}" if max_level else ""

            query = f'''
                WITH RECURSIVE expand_nodes AS (
                    -- 基础查询：查找直接子节点
                    SELECT
                        child.id,
                        child.node_name,
                        child.node_type,
                        child.display_name,
                        1 AS level,
                        child.attributes
                    FROM ontology_edges edge
                    JOIN ontology_nodes child ON edge.child_id = child.id
                    JOIN ontology_nodes parent ON edge.parent_id = parent.id
                    WHERE parent.node_name = ?

                    UNION ALL

                    -- 递归查询：查找子节点的子节点
                    SELECT
                        child.id,
                        child.node_name,
                        child.node_type,
                        child.display_name,
                        expand.level + 1,
                        child.attributes
                    FROM ontology_edges edge
                    JOIN ontology_nodes child ON edge.child_id = child.id
                    JOIN expand_nodes expand ON edge.parent_id = expand.id
                    WHERE expand.node_type = 'abstract_concept'
                    {level_filter}
                )
                SELECT DISTINCT
                    node_name,
                    display_name,
                    attributes
                FROM expand_nodes
                WHERE node_type = 'concrete_instance'
                ORDER BY node_name
            '''

            cursor.execute(query, (concept_name,))
            rows = cursor.fetchall()

            if not rows:
                logger.warning(f"概念 '{concept_name}' 没有具体实例")
                return [] if return_type != "both" else {}

            # 根据返回类型格式化结果
            if return_type == "business_name":
                return [row[0] for row in rows]
            elif return_type == "physical_code":
                codes = []
                for row in rows:
                    attrs = json.loads(row[2]) if row[2] else {}
                    code = attrs.get("code")
                    if code:
                        codes.append(code)
                return codes
            elif return_type == "both":
                result = {}
                for row in rows:
                    attrs = json.loads(row[2]) if row[2] else {}
                    code = attrs.get("code", "")
                    result[row[0]] = code
                return result
            else:
                raise ValueError(f"不支持的返回类型: {return_type}")

        finally:
            conn.close()

    def get_concept_type(self, concept_name: str) -> str:
        """
        获取概念的分类

        参数:
            concept_name: 概念名称

        返回:
            概念分类（city/customer/region/business）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT concept_category FROM ontology_nodes WHERE node_name = ?",
                (concept_name,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
            return "unknown"
        finally:
            conn.close()
# [AGC:END]
