# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
混合调度器：协调数据库查询和LLM推理
"""

# [AGC:START] tool=Cc author=fangkun
import sqlite3
import json
import logging
from typing import List, Dict, Optional

from ontology.query_engine import OntologyQueryEngine
from ontology.llm_reasoner import OntologyLLMReasoner
from ontology.normalizer import ConceptNameNormalizer

logger = logging.getLogger(__name__)


class OntologyExpander:
    """
    逻辑扩层混合调度器（步骤3.3核心实现）

    协调数据库查询和LLM推理，实现B+D策略
    """

    class ConceptNotFoundError(Exception):
        """概念未找到异常"""
        pass

    def __init__(
        self,
        db_path: str = "chatbi.db",
        model=None,
        enable_llm_reasoning: bool = True,
        enable_learning_mode: bool = False
    ):
        """
        初始化扩层器

        参数:
            db_path: 数据库路径
            model: LangChain模型
            enable_llm_reasoning: 是否启用LLM推理
            enable_learning_mode: 是否启用学习模式（回写数据库）
        """
        self.db_path = db_path
        self.query_engine = OntologyQueryEngine(db_path)
        self.llm_reasoner = OntologyLLMReasoner(model) if model and enable_llm_reasoning else None
        self.enable_llm_reasoning = enable_llm_reasoning
        self.enable_learning_mode = enable_learning_mode

    def expand(
        self,
        concept_name: str,
        concept_category: str = None,
        **kwargs
    ) -> List[str]:
        """
        执行逻辑扩层：先查数据库，未命中则LLM推理

        策略：
        1. 查询数据库
        2. 未命中 -> 调用LLM推理
        3. 可选：回写数据库（学习模式）

        参数:
            concept_name: 概念名称
            concept_category: 概念分类（自动推断或指定）
            kwargs: 其他参数（max_level, return_type等）

        返回:
            实例列表
        """
        # Step 1: Normalize concept name
        normalized_name = ConceptNameNormalizer.normalize(concept_name)

        # Step 2: Database query
        try:
            logger.info(f"数据库查询: {normalized_name}")
            result = self.query_engine.expand_concept(normalized_name, **kwargs)

            if result:
                if isinstance(result, dict):
                    return list(result.keys())
                return result
            logger.info(f"数据库未命中: {normalized_name}")

        except OntologyQueryEngine.ConceptNotFoundError:
            logger.info(f"概念在数据库中不存在: {normalized_name}")
        except Exception as e:
            logger.warning(f"数据库查询失败: {e}")

        # Step 3: LLM reasoning fallback
        if self.enable_llm_reasoning and self.llm_reasoner:
            logger.info(f"触发LLM推理: {normalized_name}")

            category = concept_category or self._infer_category(normalized_name)
            result = self.llm_reasoner.reason_concept(
                normalized_name,
                category,
                context=kwargs.get("context")
            )

            if result:
                # Step 4: Learning mode - write back to database
                if self.enable_learning_mode:
                    self._learn_from_reasoning(normalized_name, result, category)

                return result

        # Step 5: Return empty list
        logger.warning(f"扩层失败，返回空列表: {normalized_name}")
        return []

    def _infer_category(self, concept_name: str) -> str:
        """
        推断概念分类

        参数:
            concept_name: 概念名称

        返回:
            概念分类（city/customer/region/business）
        """
        concept_lower = concept_name.lower()

        if any(kw in concept_lower for kw in ["city", "cities", "城市"]):
            return "city"
        elif any(kw in concept_lower for kw in ["customer", "company", "客户", "公司"]):
            return "customer"
        elif any(kw in concept_lower for kw in ["region", "area", "区域", "地区"]):
            return "region"

        return "business"

    def _learn_from_reasoning(
        self,
        concept_name: str,
        instances: List[str],
        concept_category: str
    ):
        """
        学习模式：将LLM推理结果回写数据库

        参数:
            concept_name: 概念名称
            instances: 实例列表
            concept_category: 概念分类
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 1. Create abstract concept node
            cursor.execute("""
                INSERT OR IGNORE INTO ontology_nodes
                (node_name, node_type, concept_category, display_name)
                VALUES (?, 'abstract_concept', ?, ?)
            """, (concept_name, concept_category, concept_name))

            # Always fetch the ID (lastrowid is 0 when INSERT OR IGNORE skips)
            concept_id = cursor.execute(
                "SELECT id FROM ontology_nodes WHERE node_name = ?",
                (concept_name,)
            ).fetchone()[0]

            # 2. Create instance nodes and establish relationships
            for instance_name in instances:
                # Create instance node
                cursor.execute("""
                    INSERT OR IGNORE INTO ontology_nodes
                    (node_name, node_type, concept_category, display_name)
                    VALUES (?, 'concrete_instance', ?, ?)
                """, (instance_name, concept_category, instance_name))

                # Establish relationship
                cursor.execute("""
                    INSERT INTO ontology_edges (parent_id, child_id, relation_type)
                    SELECT ?, id, 'includes' FROM ontology_nodes WHERE node_name = ?
                """, (concept_id, instance_name))

            conn.commit()
            logger.info(f"学习模式：已将 '{concept_name}' 的 {len(instances)} 个实例写入数据库")

        except Exception as e:
            conn.rollback()
            logger.error(f"学习模式写入失败: {e}")
        finally:
            conn.close()
# [AGC:END]
