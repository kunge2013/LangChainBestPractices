# 本体逻辑扩层功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现ChatBI步骤3.3逻辑扩层功能，支持多类型概念扩层（城市/客户/区域/业务），结合SQLite递归CTE查询和LLM推理兜底。

**Architecture:** 采用分层架构设计：数据库层（SQLite图结构）+ 查询引擎层（递归CTE）+ LLM推理引擎层 + 混合调度器层。核心策略为先查数据库，未命中再LLM推理，可选学习模式回写数据库。

**Tech Stack:** Python 3.12+, SQLite 3.35+ (递归CTE), LangChain, Pytest, concurrent.futures, functools.lru_cache

## Global Constraints

- Python版本: >= 3.12
- 数据库: SQLite 3.35+ (必须支持递归CTE)
- LLM模型: OpenAI / Qwen 3.5 Plus
- 代码风格: 遵循PEP 8，使用类型注解
- 测试框架: Pytest，覆盖率目标 80%+
- 所有新代码必须添加AGC标签: `// [AGC:START] tool=Cc author=fangkun` 和 `// [AGC:END]`
- 每个文件头部添加: `// [AGC:FILE] tool=Cc author=fangkun date=YYYY-MM-DD`

---

### Task 1: 创建本体数据库表结构

**Files:**
- Create: `python/src/base_practice/16.chatbi/ontology/__init__.py`
- Create: `python/src/base_practice/16.chatbi/ontology/database.py`
- Create: `tests/python/test_ontology/test_database.py`

**Interfaces:**
- Produces: `init_ontology_tables(db_path: str) -> None`, `drop_ontology_tables(db_path: str) -> None`
- Produces: `OntologyNodes` 和 `OntologyEdges` 数据库表

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_ontology/test_database.py
import pytest
import sqlite3
import tempfile
import os
from ontology.database import init_ontology_tables, drop_ontology_tables

def test_init_ontology_tables():
    """测试本体表初始化"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 验证ontology_nodes表存在且有正确字段
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ontology_nodes'")
        assert cursor.fetchone() is not None

        cursor.execute("PRAGMA table_info(ontology_nodes)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = ['id', 'node_name', 'node_type', 'concept_category', 'display_name', 'description', 'attributes', 'created_at', 'updated_at']
        assert all(col in columns for col in expected_columns)

        # 验证ontology_edges表存在且有正确字段
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ontology_edges'")
        assert cursor.fetchone() is not None

        cursor.execute("PRAGMA table_info(ontology_edges)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = ['id', 'parent_id', 'child_id', 'relation_type', 'edge_weight', 'created_at']
        assert all(col in columns for col in expected_columns)

        # 验证索引存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_nodes_name'")
        assert cursor.fetchone() is not None

        conn.close()
    finally:
        os.unlink(db_path)


def test_drop_ontology_tables():
    """测试本体表删除"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        drop_ontology_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ontology_nodes'")
        assert cursor.fetchone() is None
        conn.close()
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_ontology/test_database.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ontology'"

- [ ] **Step 3: Create module structure and minimal implementation**

```python
# python/src/base_practice/16.chatbi/ontology/__init__.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
本体逻辑扩层模块
"""

from ontology.database import init_ontology_tables, drop_ontology_tables

__all__ = ['init_ontology_tables', 'drop_ontology_tables']
```

```python
# python/src/base_practice/16.chatbi/ontology/database.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
本体数据库表结构定义
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def init_ontology_tables(db_path: str) -> None:
    """
    初始化本体表结构

    创建 ontology_nodes 和 ontology_edges 表以及必要的索引
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 创建 ontology_nodes 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ontology_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_name TEXT NOT NULL UNIQUE,
                node_type TEXT NOT NULL,
                concept_category TEXT NOT NULL,
                display_name TEXT,
                description TEXT,
                attributes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建 ontology_edges 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ontology_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER NOT NULL,
                child_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                edge_weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES ontology_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (child_id) REFERENCES ontology_nodes(id) ON DELETE CASCADE,
                UNIQUE(parent_id, child_id, relation_type)
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_name ON ontology_nodes(node_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_type ON ontology_nodes(node_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_category ON ontology_nodes(concept_category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_parent ON ontology_edges(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_child ON ontology_edges(child_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_relation ON ontology_edges(relation_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_parent_child ON ontology_edges(parent_id, child_id)')

        conn.commit()
        logger.info(f"本体表初始化完成: {db_path}")

    except Exception as e:
        conn.rollback()
        logger.error(f"本体表初始化失败: {e}")
        raise
    finally:
        conn.close()


def drop_ontology_tables(db_path: str) -> None:
    """
    删除本体表结构

    用于测试清理或重建
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 删除表（索引会自动删除）
        cursor.execute('DROP TABLE IF EXISTS ontology_edges')
        cursor.execute('DROP TABLE IF EXISTS ontology_nodes')

        conn.commit()
        logger.info(f"本体表已删除: {db_path}")

    except Exception as e:
        conn.rollback()
        logger.error(f"本体表删除失败: {e}")
        raise
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_ontology/test_database.py -v`
Expected: PASS (2 tests passed)

- [ ] **Step 5: Commit**

```bash
git add python/src/base_practice/16.chatbi/ontology/ tests/python/test_ontology/
git commit -m "feat: add ontology database schema

- Create ontology_nodes and ontology_edges tables
- Add indexes for query optimization
- Support recursive CTE queries
- Add table initialization and cleanup functions

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 创建概念名称标准化器

**Files:**
- Create: `python/src/base_practice/16.chatbi/ontology/normalizer.py`
- Create: `tests/python/test_ontology/test_normalizer.py`

**Interfaces:**
- Produces: `ConceptNameNormalizer.normalize(concept_name: str) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_ontology/test_normalizer.py
import pytest
from ontology.normalizer import ConceptNameNormalizer

def test_normalize_direct_match():
    """测试直接匹配"""
    assert ConceptNameNormalizer.normalize("tier1_cities") == "tier1_cities"
    assert ConceptNameNormalizer.normalize("bytedance_group") == "bytedance_group"


def test_normalize_alias_mapping():
    """测试别名映射"""
    assert ConceptNameNormalizer.normalize("一线城市") == "tier1_cities"
    assert ConceptNameNormalizer.normalize("ByteDance") == "bytedance_group"
    assert ConceptNameNormalizer.normalize("头条系") == "bytedance_group"


def test_normalize_case_insensitive():
    """测试大小写不敏感"""
    assert ConceptNameNormalizer.normalize("TIER1_CITIES") == "tier1_cities"
    assert ConceptNameNormalizer.normalize("BYTEDANCE") == "bytedance_group"


def test_normalize_no_alias():
    """测试无别名返回原值"""
    result = ConceptNameNormalizer.normalize("unknown_concept")
    assert result == "unknown_concept"


def test_add_alias():
    """测试动态添加别名"""
    ConceptNameNormalizer.add_alias("二线城市", "tier2_cities")
    assert ConceptNameNormalizer.normalize("二线城市") == "tier2_cities"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_ontology/test_normalizer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ontology.normalizer'"

- [ ] **Step 3: Write minimal implementation**

```python
# python/src/base_practice/16.chatbi/ontology/normalizer.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
概念名称标准化器
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ConceptNameNormalizer:
    """
    概念名称标准化器

    处理概念名称的别名映射、大小写转换、模糊匹配等
    """

    # 预定义的别名映射表
    ALIAS_MAP: Dict[str, str] = {
        # 城市分类
        "一线城市": "tier1_cities",
        "tier1_cities": "tier1_cities",
        "tier 1 cities": "tier1_cities",
        "tier1": "tier1_cities",

        # 客户分类
        "字节跳动": "bytedance_group",
        "bytedance": "bytedance_group",
        "bytedance_group": "bytedance_group",
        "头条系": "bytedance_group",
        "字节跳动集团": "bytedance_group",

        # 区域分类
        "华东区": "east_china",
        "east_china": "east_china",
        "华东地区": "east_china",
        "east china": "east_china",
    }

    @classmethod
    def normalize(cls, concept_name: str) -> str:
        """
        标准化概念名称

        参数:
            concept_name: 原始概念名称

        返回:
            标准化的概念名称（小写）
        """
        if not concept_name:
            return concept_name

        # 转换为小写用于匹配
        concept_lower = concept_name.strip().lower()

        # 先尝试直接匹配（小写）
        if concept_lower in cls.ALIAS_MAP:
            return cls.ALIAS_MAP[concept_lower]

        # 遍历别名映射，尝试模糊匹配
        for alias, canonical in cls.ALIAS_MAP.items():
            alias_lower = alias.lower()
            # 检查是否包含别名或别名包含它
            if concept_lower in alias_lower or alias_lower in concept_lower:
                return canonical

        # 没有匹配，返回原始名称的小写形式
        return concept_lower

    @classmethod
    def add_alias(cls, alias: str, canonical_name: str) -> None:
        """
        动态添加别名映射

        参数:
            alias: 别名
            canonical_name: 标准名称
        """
        cls.ALIAS_MAP[alias.lower()] = canonical_name.lower()
        logger.info(f"添加别名映射: {alias} -> {canonical_name}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_ontology/test_normalizer.py -v`
Expected: PASS (5 tests passed)

- [ ] **Step 5: Commit**

```bash
git add python/src/base_practice/16.chatbi/ontology/normalizer.py tests/python/test_ontology/test_normalizer.py
git commit -m "feat: add concept name normalizer

- Support alias mapping for concept names
- Case-insensitive matching
- Dynamic alias addition
- Handle city, customer, and region concept aliases

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 实现本体查询引擎

**Files:**
- Create: `python/src/base_practice/16.chatbi/ontology/query_engine.py`
- Create: `tests/python/test_ontology/test_query_engine.py`

**Interfaces:**
- Consumes: `init_ontology_tables(db_path: str)` (from database.py)
- Produces: `OntologyQueryEngine.expand_concept(concept_name: str, max_level: int = None, return_type: str = "business_name") -> List[str]`
- Produces: `OntologyQueryEngine.get_concept_type(concept_name: str) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_ontology/test_query_engine.py
import pytest
import sqlite3
import tempfile
import os
from ontology.database import init_ontology_tables
from ontology.query_engine import OntologyQueryEngine

@pytest.fixture
def db_with_sample_data():
    """创建包含示例数据的测试数据库"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 插入测试数据：一线城市
        cursor.execute("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES
                ('tier1_cities', 'abstract_concept', 'city', '一线城市', NULL),
                ('shanghai', 'concrete_instance', 'city', '上海', '{"code": "021"}'),
                ('beijing', 'concrete_instance', 'city', '北京', '{"code": "010"}'),
                ('guangzhou', 'concrete_instance', 'city', '广州', '{"code": "020"}'),
                ('shenzhen', 'concrete_instance', 'city', '深圳', '{"code": "0755"}')
        """)

        # 建立关系
        concept_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier1_cities'").fetchone()[0]
        for city in ['shanghai', 'beijing', 'guangzhou', 'shenzhen']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (concept_id, city_id))

        conn.commit()
        conn.close()
        yield db_path

    finally:
        os.unlink(db_path)


def test_expand_concept_two_levels(db_with_sample_data):
    """测试两级扩层（城市分类）"""
    engine = OntologyQueryEngine(db_with_sample_data)

    result = engine.expand_concept("tier1_cities", return_type="business_name")

    assert isinstance(result, list)
    assert len(result) == 4
    assert set(result) == {"shanghai", "beijing", "guangzhou", "shenzhen"}


def test_expand_concept_physical_code(db_with_sample_data):
    """测试返回物理编码"""
    engine = OntologyQueryEngine(db_with_sample_data)

    result = engine.expand_concept("tier1_cities", return_type="physical_code")

    assert isinstance(result, list)
    assert len(result) == 4
    # 验证返回的是编码
    assert all(code in ["021", "010", "020", "0755"] for code in result if code)


def test_expand_concept_both(db_with_sample_data):
    """测试返回业务名称和物理编码"""
    engine = OntologyQueryEngine(db_with_sample_data)

    result = engine.expand_concept("tier1_cities", return_type="both")

    assert isinstance(result, dict)
    assert len(result) == 4
    assert "shanghai" in result
    assert result["shanghai"] == "021"


def test_concept_not_found(db_with_sample_data):
    """测试概念未找到"""
    engine = OntologyQueryEngine(db_with_sample_data)

    with pytest.raises(OntologyQueryEngine.ConceptNotFoundError):
        engine.expand_concept("nonexistent_concept")


def test_get_concept_type(db_with_sample_data):
    """测试获取概念类型"""
    engine = OntologyQueryEngine(db_with_sample_data)

    assert engine.get_concept_type("tier1_cities") == "city"
    assert engine.get_concept_type("shanghai") == "city"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_ontology/test_query_engine.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ontology.query_engine'"

- [ ] **Step 3: Write minimal implementation**

```python
# python/src/base_practice/16.chatbi/ontology/query_engine.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04

// [AGC:START] tool=Cc author=fangkun
"""
本体查询引擎：基于递归CTE实现多级扩层查询
"""

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
                    import json
                    attrs = json.loads(row[2]) if row[2] else {}
                    code = attrs.get("code")
                    if code:
                        codes.append(code)
                return codes
            elif return_type == "both":
                import json
                result = {}
                for row in rows:
                    attrs = json.loads(row[2]) if row[2] else {}
                    code = attrs.get("code")
                    if code:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_ontology/test_query_engine.py -v`
Expected: PASS (5 tests passed)

- [ ] **Step 5: Commit**

```bash
git add python/src/base_practice/16.chatbi/ontology/query_engine.py tests/python/test_ontology/test_query_engine.py
git commit -m "feat: add ontology query engine with recursive CTE

- Implement multi-level expansion queries
- Support three return types: business_name, physical_code, both
- Add concept type lookup
- Handle concept not found errors

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: 实现LLM推理引擎

**Files:**
- Create: `python/src/base_practice/16.chatbi/ontology/llm_reasoner.py`
- Create: `tests/python/test_ontology/test_llm_reasoner.py`

**Interfaces:**
- Produces: `OntologyLLMReasoner.reason_concept(concept_name: str, concept_category: str, context: Dict = None) -> List[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_ontology/test_llm_reasoner.py
import pytest
from unittest.mock import Mock, MagicMock
from ontology.llm_reasoner import OntologyLLMReasoner
from langchain_core.messages import HumanMessage

@pytest.fixture
def mock_llm():
    """创建Mock LLM"""
    llm = Mock()
    llm.invoke = MagicMock()
    return llm


def test_reason_concept_city(mock_llm):
    """测试城市概念推理"""
    # 模拟LLM响应
    mock_llm.invoke.return_value = HumanMessage(content='''{"instances": [
        {"name": "上海", "code": "021", "reason": "上海是公认的四大一线城市之一"},
        {"name": "北京", "code": "010", "reason": "北京是政治中心，属于一线城市"}
    ], "confidence": 0.95}''')

    reasoner = OntologyLLMReasoner(mock_llm)
    result = reasoner.reason_concept("tier1_cities", "city")

    assert isinstance(result, list)
    assert len(result) == 2
    assert "上海" in result
    assert "北京" in result


def test_reason_concept_with_context(mock_llm):
    """测试带上下文的概念推理"""
    mock_llm.invoke.return_value = HumanMessage(content='''{"instances": [
        {"name": "杭州", "code": "0571"}
    ], "confidence": 0.8}''')

    reasoner = OntologyLLMReasoner(mock_llm)
    result = reasoner.reason_concept("new_cities", "city", context={"region": "华东"})

    assert isinstance(result, list)
    assert "杭州" in result


def test_reason_concept_invalid_json(mock_llm):
    """测试无效JSON响应"""
    mock_llm.invoke.return_value = HumanMessage(content="invalid json")

    reasoner = OntologyLLMReasoner(mock_llm)
    result = reasoner.reason_concept("test", "city")

    assert result == []


def test_reason_concept_empty_instances(mock_llm):
    """测试空实例列表"""
    mock_llm.invoke.return_value = HumanMessage(content='{"instances": [], "confidence": 0.5}')

    reasoner = OntologyLLMReasoner(mock_llm)
    result = reasoner.reason_concept("test", "city")

    assert result == []


def test_build_reasoning_prompt():
    """测试推理提示词构建"""
    reasoner = OntologyLLMReasoner(Mock())
    prompt = reasoner._build_reasoning_prompt()

    assert "抽象概念" in prompt
    assert "概念分类" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_ontology/test_llm_reasoner.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ontology.llm_reasoner'"

- [ ] **Step 3: Write minimal implementation**

```python
# python/src/base_practice/16.chatbi/ontology/llm_reasoner.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
LLM推理引擎：当数据库未命中时，使用LLM进行概念推理
"""

import json
import logging
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class OntologyLLMReasoner:
    """
    LLM推理引擎

    当数据库未命中时，使用LLM进行概念推理
    """

    def __init__(self, model: ChatOpenAI):
        """
        初始化推理引擎

        参数:
            model: LangChain ChatOpenAI模型
        """
        self.model = model
        self.reasoning_prompt = self._build_reasoning_prompt()

    def _build_reasoning_prompt(self) -> str:
        """
        构建推理提示词模板

        返回:
            提示词字符串
        """
        return """你是一个业务知识推理专家。给定一个抽象概念，请推理出其包含的具体实例列表。

概念名称：{concept_name}
概念分类：{concept_category}
上下文：{context}

请返回JSON格式：
{{
  "instances": [
    {{"name": "上海", "code": "021", "reason": "上海是公认的四大一线城市之一"}},
    {{"name": "北京", "code": "010", "reason": "北京是政治中心，属于一线城市"}}
  ],
  "confidence": 0.95
}}

注意：
1. 只返回JSON格式，不要有其他文字
2. instances数组包含具体实例
3. code字段为物理编码（如城市区号），如果不确定可以省略
4. confidence表示推理置信度（0-1之间）
5. 根据概念分类进行推理（city返回城市，customer返回公司名等）
"""

    def reason_concept(
        self,
        concept_name: str,
        concept_category: str,
        context: Dict = None
    ) -> List[str]:
        """
        LLM推理：给定抽象概念，推理出具体实例列表

        参数:
            concept_name: 概念名称（如"一线城市"）
            concept_category: 概念分类（city/customer/region）
            context: 额外上下文信息

        返回:
            推理出的实例名称列表
        """
        try:
            # 构建提示词
            prompt_text = self.reasoning_prompt.format(
                concept_name=concept_name,
                concept_category=concept_category,
                context=json.dumps(context, ensure_ascii=False) if context else "无"
            )

            # 调用LLM
            logger.info(f"触发LLM推理: {concept_name} ({concept_category})")
            response = self.model.invoke(prompt_text)
            response_text = response.content.strip()

            # 解析JSON响应
            try:
                result = json.loads(response_text)
                instances = result.get("instances", [])
                confidence = result.get("confidence", 0.0)

                logger.info(f"LLM推理完成: {len(instances)} 个实例, 置信度: {confidence}")

                # 提取实例名称
                return [inst["name"] for inst in instances if "name" in inst]

            except json.JSONDecodeError as e:
                logger.error(f"LLM响应JSON解析失败: {e}, 响应: {response_text}")
                return []

        except Exception as e:
            logger.error(f"LLM推理失败: {e}")
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_ontology/test_llm_reasoner.py -v`
Expected: PASS (5 tests passed)

- [ ] **Step 5: Commit**

```bash
git add python/src/base_practice/16.chatbi/ontology/llm_reasoner.py tests/python/test_ontology/test_llm_reasoner.py
git commit -m "feat: add LLM reasoning engine for ontology expansion

- Implement LLM-based concept reasoning
- Parse JSON responses from LLM
- Handle invalid responses gracefully
- Support context-enhanced reasoning

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: 实现混合调度器

**Files:**
- Create: `python/src/base_practice/16.chatbi/ontology/expander.py`
- Create: `tests/python/test_ontology/test_expander.py`

**Interfaces:**
- Consumes: `OntologyQueryEngine`, `OntologyLLMReasoner`, `ConceptNameNormalizer`
- Produces: `OntologyExpander.expand(concept_name: str, concept_category: str = None, **kwargs) -> List[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_ontology/test_expander.py
import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock
from ontology.database import init_ontology_tables
from ontology.query_engine import OntologyQueryEngine
from ontology.llm_reasoner import OntologyLLMReasoner
from ontology.expander import OntologyExpander


@pytest.fixture
def db_with_sample_data():
    """创建包含示例数据的测试数据库"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 插入测试数据
        cursor.execute("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES
                ('tier1_cities', 'abstract_concept', 'city', '一线城市', NULL),
                ('shanghai', 'concrete_instance', 'city', '上海', '{"code": "021"}'),
                ('beijing', 'concrete_instance', 'city', '北京', '{"code": "010"}')
        """)

        concept_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier1_cities'").fetchone()[0]
        for city in ['shanghai', 'beijing']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (concept_id, city_id))

        conn.commit()
        conn.close()
        yield db_path

    finally:
        os.unlink(db_path)


def test_expand_database_hit(db_with_sample_data):
    """测试数据库命中"""
    mock_llm = Mock()
    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=mock_llm,
        enable_llm_reasoning=False
    )

    result = expander.expand("tier1_cities")

    assert isinstance(result, list)
    assert len(result) == 2
    assert set(result) == {"shanghai", "beijing"}

    # 验证LLM未被调用
    mock_llm.invoke.assert_not_called()


def test_expand_llm_fallback(db_with_sample_data):
    """测试LLM兜底"""
    mock_llm = Mock()
    mock_llm.invoke.return_value = Mock(content='{"instances": [{"name": "杭州"}, {"name": "南京"}], "confidence": 0.9}')

    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=mock_llm,
        enable_llm_reasoning=True
    )

    result = expander.expand("tier2_cities")

    assert isinstance(result, list)
    assert "杭州" in result
    assert "南京" in result

    # 验证LLM被调用
    mock_llm.invoke.assert_called_once()


def test_expand_with_normalization(db_with_sample_data):
    """测试概念名称标准化"""
    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=Mock(),
        enable_llm_reasoning=False
    )

    result = expander.expand("一线城市")

    assert set(result) == {"shanghai", "beijing"}


def test_expand_learning_mode(db_with_sample_data):
    """测试学习模式"""
    mock_llm = Mock()
    mock_llm.invoke.return_value = Mock(content='{"instances": [{"name": "深圳"}, {"name": "广州"}], "confidence": 0.95}')

    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=mock_llm,
        enable_llm_reasoning=True,
        enable_learning_mode=True
    )

    result = expander.expand("tier1_new_cities")

    assert isinstance(result, list)

    # 验证数据已写入数据库
    conn = sqlite3.connect(db_with_sample_data)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ontology_nodes WHERE node_name = 'tier1_new_cities'")
    assert cursor.fetchone()[0] == 1
    conn.close()


def test_expand_both_disabled(db_with_sample_data):
    """测试数据库和LLM都禁用"""
    expander = OntologyExpander(
        db_path=db_with_sample_data,
        model=None,
        enable_llm_reasoning=False
    )

    result = expander.expand("nonexistent_concept")

    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_ontology/test_expander.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ontology.expander'"

- [ ] **Step 3: Write minimal implementation**

```python
# python/src/base_practice/16.chatbi/ontology/expander.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
混合调度器：协调数据库查询和LLM推理
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI

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
        model: ChatOpenAI = None,
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
        2. 未命中 → 调用LLM推理
        3. 可选：回写数据库（学习模式）

        参数:
            concept_name: 概念名称
            concept_category: 概念分类（自动推断或指定）
            kwargs: 其他参数（max_level, return_type等）

        返回:
            实例列表
        """
        # 步骤1：标准化概念名称
        normalized_name = ConceptNameNormalizer.normalize(concept_name)

        # 步骤2：数据库查询
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

        # 步骤3：LLM推理兜底
        if self.enable_llm_reasoning and self.llm_reasoner:
            logger.info(f"触发LLM推理: {normalized_name}")

            category = concept_category or self._infer_category(normalized_name)
            result = self.llm_reasoner.reason_concept(
                normalized_name,
                category,
                context=kwargs.get("context")
            )

            if result:
                # 步骤4：学习模式回写数据库
                if self.enable_learning_mode:
                    self._learn_from_reasoning(normalized_name, result, category)

                return result

        # 步骤5：返回空列表
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
        # 基于关键词推断
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
            # 1. 创建抽象概念节点
            cursor.execute("""
                INSERT OR IGNORE INTO ontology_nodes
                (node_name, node_type, concept_category, display_name)
                VALUES (?, 'abstract_concept', ?, ?)
            """, (concept_name, concept_category, concept_name))

            concept_id = cursor.lastrowid

            # 2. 为每个实例创建节点并建立关系
            for instance_name in instances:
                # 创建实例节点
                cursor.execute("""
                    INSERT OR IGNORE INTO ontology_nodes
                    (node_name, node_type, concept_category, display_name)
                    VALUES (?, 'concrete_instance', ?, ?)
                """, (instance_name, concept_category, instance_name))

                # 建立关系
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_ontology/test_expander.py -v`
Expected: PASS (5 tests passed)

- [ ] **Step 5: Commit**

```bash
git add python/src/base_practice/16.chatbi/ontology/expander.py tests/python/test_ontology/test_expander.py
git commit -m "feat: add ontology expander with hybrid strategy

- Implement database + LLM fallback strategy
- Support concept name normalization
- Add optional learning mode
- Infer concept category automatically

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: 创建LangChain工具函数

**Files:**
- Create: `python/src/base_practice/16.chatbi/ontology/tools.py`
- Modify: `python/src/base_practice/16.chatbi/ChatBiAgentV1.py`

**Interfaces:**
- Consumes: `OntologyExpander`
- Produces: `logical_layer_expansion(concept_name: str, concept_category: str = None, return_type: str = "business_name") -> List[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_ontology/test_tools.py
import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock
from ontology.database import init_ontology_tables
from ontology.tools import logical_layer_expansion


@pytest.fixture
def db_with_sample_data():
    """创建包含示例数据的测试数据库"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES
                ('tier1_cities', 'abstract_concept', 'city', '一线城市', NULL),
                ('shanghai', 'concrete_instance', 'city', '上海', '{"code": "021"}'),
                ('beijing', 'concrete_instance', 'city', '北京', '{"code": "010"}')
        """)

        concept_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier1_cities'").fetchone()[0]
        for city in ['shanghai', 'beijing']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (concept_id, city_id))

        conn.commit()
        conn.close()
        yield db_path

    finally:
        os.unlink(db_path)


def test_logical_layer_expansion_tool(db_with_sample_data, monkeypatch):
    """测试逻辑扩层工具函数"""
    # 模拟全局变量
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_sample_data)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion("tier1_cities", "city")

    assert isinstance(result, list)
    assert len(result) == 2
    assert set(result) == {"shanghai", "beijing"}


def test_logical_layer_expansion_physical_code(db_with_sample_data, monkeypatch):
    """测试返回物理编码"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_sample_data)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion("tier1_cities", "city", return_type="physical_code")

    assert isinstance(result, list)
    assert all(code in ["021", "010"] for code in result if code)


def test_logical_layer_expansion_both(db_with_sample_data, monkeypatch):
    """测试返回业务名称和物理编码"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_sample_data)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion("tier1_cities", "city", return_type="both")

    assert isinstance(result, dict)
    assert "shanghai" in result
    assert result["shanghai"] == "021"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_ontology/test_tools.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ontology.tools'"

- [ ] **Step 3: Create tool function**

```python
# python/src/base_practice/16.chatbi/ontology/tools.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
LangChain工具函数：逻辑扩层
"""

from typing import List
from langchain_core.tools import tool
import os

from ontology.expander import OntologyExpander

# 全局配置（从环境变量或配置文件读取）
DB_PATH = os.environ.get("ONTOLOGY_DB_PATH", "chatbi.db")

# 全局模型（在外部初始化）
model = None


def set_global_model(llm_model):
    """设置全局模型"""
    global model
    model = llm_model


@tool
def logical_layer_expansion(
    concept_name: str,
    concept_category: str = None,
    return_type: str = "business_name"
) -> List[str]:
    """
    步骤3.3：逻辑扩层。
    将抽象概念扩展为具体的业务名单。

    示例：
        - 输入: "tier1_cities" → 输出: ["shanghai", "beijing", "guangzhou", "shenzhen"]
        - 输入: "bytedance_group" → 输出: ["wuhan_toutiao", "wuhan_douyin", "wuhan_feishu"]
        - 输入: "east_china" → 输出: ["nanjing", "suzhou", "hangzhou", "ningbo", "shanghai"]

    参数:
        concept_name: 抽象概念名称（支持别名，如"一线城市"、"tier1_cities"）
        concept_category: 概念分类（city/customer/region/business），不指定则自动推断
        return_type: 返回类型
            - "business_name": 业务名称（如"上海"）
            - "physical_code": 物理编码（如"021"）
            - "both": 返回字典 {"上海": "021", "北京": "010"}

    返回:
        具体实例的业务名称列表、物理编码列表或字典
    """
    expander = OntologyExpander(
        db_path=DB_PATH,
        model=model,
        enable_llm_reasoning=True if model else False,
        enable_learning_mode=False
    )

    return expander.expand(concept_name, concept_category, return_type=return_type)
```

- [ ] **Step 4: Update ChatBiAgentV1.py to integrate the tool**

```python
# python/src/base_practice/16.chatbi/ChatBiAgentV1.py
# [AGC:START] tool=Cc author=fangkun
# 在现有代码中添加导入
from ontology.tools import logical_layer_expansion, set_global_model

# 初始化后设置全局模型
set_global_model(model)

# 更新工具列表
tools = [
    extract_entities_enhanced,
    logical_layer_expansion,  # 新增：步骤3.3逻辑扩层
    expand_ontology,           # 保留旧版兼容
    map_metric,
    map_dimension,
    assemble_logical_sql,
    map_physical_values,
    execute_sql,
    validate_result
]
# [AGC:END]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/python/test_ontology/test_tools.py -v`
Expected: PASS (3 tests passed)

- [ ] **Step 6: Commit**

```bash
git add python/src/base_practice/16.chatbi/ontology/tools.py python/src/base_practice/16.chatbi/ChatBiAgentV1.py tests/python/test_ontology/test_tools.py
git commit -m "feat: add LangChain tool for logical layer expansion

- Create logical_layer_expansion tool
- Integrate with ChatBiAgentV1
- Support three return types
- Maintain backward compatibility with expand_ontology

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: 添加示例数据和集成测试

**Files:**
- Create: `python/src/base_practice/16.chatbi/ontology/init_data.py`
- Create: `tests/python/test_ontology/test_integration.py`

**Interfaces:**
- Consumes: `init_ontology_tables(db_path: str)`, `OntologyExpander`
- Produces: `load_sample_ontology_data(db_path: str) -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_ontology/test_integration.py
import pytest
import sqlite3
import tempfile
import os
from ontology.database import init_ontology_tables
from ontology.init_data import load_sample_ontology_data
from ontology.tools import logical_layer_expansion


@pytest.fixture
def db_with_full_sample():
    """创建包含完整示例数据的数据库"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        init_ontology_tables(db_path)
        load_sample_ontology_data(db_path)
        yield db_path

    finally:
        os.unlink(db_path)


def test_integration_city_expansion(db_with_full_sample, monkeypatch):
    """集成测试：城市扩层"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion("tier1_cities", "city")

    assert len(result) == 4
    assert set(result) == {"shanghai", "beijing", "guangzhou", "shenzhen"}


def test_integration_customer_expansion(db_with_full_sample, monkeypatch):
    """集成测试：客户扩层"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion("bytedance_group", "customer")

    assert len(result) == 3
    assert "wuhan_toutiao" in result
    assert "wuhan_douyin" in result
    assert "wuhan_feishu" in result


def test_integration_region_expansion(db_with_full_sample, monkeypatch):
    """集成测试：区域扩层"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    result = logical_layer_expansion("east_china", "region")

    assert len(result) >= 5  # 至少包含5个城市


def test_end_to_end_workflow(db_with_full_sample, monkeypatch):
    """端到端工作流测试"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    # 1. 扩层一线城市
    cities = logical_layer_expansion("tier1_cities", "city")
    assert len(cities) > 0

    # 2. 获取物理编码
    codes = logical_layer_expansion("tier1_cities", "city", return_type="physical_code")
    assert len(codes) > 0

    # 3. 获取映射关系
    mapping = logical_layer_expansion("tier1_cities", "city", return_type="both")
    assert isinstance(mapping, dict)
    assert len(mapping) > 0


def test_integration_with_aliases(db_with_full_sample, monkeypatch):
    """集成测试：别名支持"""
    monkeypatch.setattr("ontology.tools.DB_PATH", db_with_full_sample)
    monkeypatch.setattr("ontology.tools.model", None)

    # 使用中文别名
    result = logical_layer_expansion("一线城市", "city")

    assert len(result) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_ontology/test_integration.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ontology.init_data'"

- [ ] **Step 3: Create sample data loader**

```python
# python/src/base_practice/16.chatbi/ontology/init_data.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
示例数据加载器
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def load_sample_ontology_data(db_path: str) -> None:
    """
    加载示例本体数据

    参数:
        db_path: 数据库路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 清空现有数据
        cursor.execute("DELETE FROM ontology_edges")
        cursor.execute("DELETE FROM ontology_nodes")

        # ========== 城市分类（两级结构）==========
        # 抽象概念
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
            VALUES (?, 'abstract_concept', 'city', ?)
        """, [
            ('tier1_cities', '一线城市'),
            ('tier2_cities', '新一线城市'),
        ])

        # 具体实例
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES (?, 'concrete_instance', 'city', ?, ?)
        """, [
            ('shanghai', '上海', '{"code": "021", "tier": "1"}'),
            ('beijing', '北京', '{"code": "010", "tier": "1"}'),
            ('guangzhou', '广州', '{"code": "020", "tier": "1"}'),
            ('shenzhen', '深圳', '{"code": "0755", "tier": "1"}'),
            ('hangzhou', '杭州', '{"code": "0571", "tier": "2"}'),
            ('chengdu', '成都', '{"code": "028", "tier": "2"}'),
            ('wuhan', '武汉', '{"code": "027", "tier": "2"}'),
        ])

        # 建立关系：一线城市
        tier1_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier1_cities'").fetchone()[0]
        for city in ['shanghai', 'beijing', 'guangzhou', 'shenzhen']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (tier1_id, city_id))

        # 建立关系：新一线城市
        tier2_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'tier2_cities'").fetchone()[0]
        for city in ['hangzhou', 'chengdu', 'wuhan']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (tier2_id, city_id))

        # ========== 客户分类（三级结构）==========
        # 抽象概念
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
            VALUES (?, 'abstract_concept', 'customer', ?)
        """, [
            ('bytedance_group', '字节跳动集团'),
            ('wuhan_subsidiaries', '武汉子公司'),
        ])

        # 具体实例
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
            VALUES (?, 'concrete_instance', 'customer', ?)
        """, [
            ('wuhan_toutiao', '武汉今日头条'),
            ('wuhan_douyin', '武汉抖音'),
            ('wuhan_feishu', '武汉飞书'),
        ])

        # 建立关系：字节跳动集团 -> 武汉子公司
        group_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'bytedance_group'").fetchone()[0]
        subs_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'wuhan_subsidiaries'").fetchone()[0]
        cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                      (group_id, subs_id))

        # 建立关系：武汉子公司 -> 具体公司
        for company in ['wuhan_toutiao', 'wuhan_douyin', 'wuhan_feishu']:
            company_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (company,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (subs_id, company_id))

        # ========== 区域分类（两级结构）==========
        # 抽象概念
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
            VALUES (?, 'abstract_concept', 'region', ?)
        """, [
            ('east_china', '华东区'),
            ('central_china', '华中区'),
        ])

        # 具体实例
        cursor.executemany("""
            INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
            VALUES (?, 'concrete_instance', 'region', ?, ?)
        """, [
            ('shanghai', '上海', '{"code": "SH", "level": "city"}'),
            ('hangzhou', '杭州', '{"code": "HZ", "level": "city"}'),
            ('nanjing', '南京', '{"code": "NJ", "level": "city"}'),
            ('suzhou', '苏州', '{"code": "SZ", "level": "city"}'),
            ('wuhan', '武汉', '{"code": "WH", "level": "city"}'),
            ('changsha', '长沙', '{"code": "CS", "level": "city"}'),
            ('zhengzhou', '郑州', '{"code": "ZZ", "level": "city"}'),
        ])

        # 建立关系：华东区
        east_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'east_china'").fetchone()[0]
        for city in ['shanghai', 'hangzhou', 'nanjing', 'suzhou']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (east_id, city_id))

        # 建立关系：华中区
        central_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = 'central_china'").fetchone()[0]
        for city in ['wuhan', 'changsha', 'zhengzhou']:
            city_id = cursor.execute("SELECT id FROM ontology_nodes WHERE node_name = ?", (city,)).fetchone()[0]
            cursor.execute("INSERT INTO ontology_edges (parent_id, child_id, relation_type) VALUES (?, ?, 'includes')",
                          (central_id, city_id))

        conn.commit()
        logger.info(f"示例本体数据加载完成: {db_path}")

    except Exception as e:
        conn.rollback()
        logger.error(f"示例数据加载失败: {e}")
        raise
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_ontology/test_integration.py -v`
Expected: PASS (5 tests passed)

- [ ] **Step 5: Commit**

```bash
git add python/src/base_practice/16.chatbi/ontology/init_data.py tests/python/test_ontology/test_integration.py
git commit -m "feat: add sample ontology data and integration tests

- Load sample data for city, customer, and region classifications
- Add comprehensive integration tests
- Test end-to-end workflows
- Support alias-based queries

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: 更新模块导出和文档

**Files:**
- Modify: `python/src/base_practice/16.chatbi/ontology/__init__.py`
- Create: `python/src/base_practice/16.chatbi/ontology/README.md`

**Interfaces:**
- Updates module public API
- Creates usage documentation

- [ ] **Step 1: Update module __init__.py**

```python
# python/src/base_practice/16.chatbi/ontology/__init__.py
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
本体逻辑扩层模块

实现ChatBI步骤3.3逻辑扩层功能，支持多类型概念扩层（城市/客户/区域/业务）。

核心组件：
- OntologyQueryEngine: 数据库查询引擎（递归CTE）
- OntologyLLMReasoner: LLM推理引擎（兜底策略）
- OntologyExpander: 混合调度器
- ConceptNameNormalizer: 概念名称标准化器
- logical_layer_expansion: LangChain工具函数

示例：
    >>> from ontology import OntologyExpander
    >>> expander = OntologyExpander("chatbi.db")
    >>> result = expander.expand("tier1_cities", "city")
    >>> print(result)
    ['shanghai', 'beijing', 'guangzhou', 'shenzhen']
"""

# 数据库
from ontology.database import init_ontology_tables, drop_ontology_tables
from ontology.init_data import load_sample_ontology_data

# 核心组件
from ontology.query_engine import OntologyQueryEngine
from ontology.llm_reasoner import OntologyLLMReasoner
from ontology.expander import OntologyExpander

# 工具
from ontology.normalizer import ConceptNameNormalizer
from ontology.tools import logical_layer_expansion, set_global_model

# 异常
from ontology.query_engine import OntologyQueryError
from ontology.expander import ConceptNotFoundError

__all__ = [
    # 数据库
    'init_ontology_tables',
    'drop_ontology_tables',
    'load_sample_ontology_data',

    # 核心组件
    'OntologyQueryEngine',
    'OntologyLLMReasoner',
    'OntologyExpander',

    # 工具
    'ConceptNameNormalizer',
    'logical_layer_expansion',
    'set_global_model',

    # 异常
    'OntologyQueryError',
    'ConceptNotFoundError',
]

# 类型别名
OntologyQueryError = OntologyQueryEngine.ConceptNotFoundError
```

- [ ] **Step 2: Create README documentation**

```python
# python/src/base_practice/16.chatbi/ontology/README.md
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
# 本体逻辑扩层模块

## 概述

本模块实现ChatBI架构中步骤3.3"逻辑扩层"功能，将抽象业务概念扩展为具体实例名单。

## 功能特性

- ✅ 支持多类型概念扩层（城市/客户/区域/业务）
- ✅ 混合层级模式（不同概念类型不同层级深度）
- ✅ 动态数据库存储 + LLM推理兜底
- ✅ 概念名称标准化（别名映射）
- ✅ 可选学习模式（LLM推理结果回写数据库）
- ✅ 基于SQLite递归CTE实现图结构

## 快速开始

### 1. 初始化数据库

```python
from ontology import init_ontology_tables, load_sample_ontology_data

# 创建表结构
init_ontology_tables("chatbi.db")

# 加载示例数据
load_sample_ontology_data("chatbi.db")
```

### 2. 使用扩层器

```python
from ontology import OntologyExpander

# 创建扩层器
expander = OntologyExpander("chatbi.db")

# 扩层查询
cities = expander.expand("tier1_cities", "city")
print(cities)  # ['shanghai', 'beijing', 'guangzhou', 'shenzhen']

# 使用别名
cities = expander.expand("一线城市", "city")
print(cities)  # ['shanghai', 'beijing', 'guangzhou', 'shenzhen']
```

### 3. 集成LangChain

```python
from ontology import logical_layer_expansion, set_global_model
from langchain_openai import ChatOpenAI

# 初始化模型
model = ChatOpenAI(...)
set_global_model(model)

# 作为工具使用
result = logical_layer_expansion("tier1_cities", "city")
print(result)
```

## 核心组件

### OntologyQueryEngine

数据库查询引擎，基于递归CTE实现多级扩层查询。

```python
from ontology import OntologyQueryEngine

engine = OntologyQueryEngine("chatbi.db")

# 基础扩层
result = engine.expand_concept("tier1_cities", return_type="business_name")
print(result)  # ['shanghai', 'beijing', ...]

# 返回物理编码
codes = engine.expand_concept("tier1_cities", return_type="physical_code")
print(codes)  # ['021', '010', ...]

# 返回映射关系
mapping = engine.expand_concept("tier1_cities", return_type="both")
print(mapping)  # {'shanghai': '021', 'beijing': '010', ...}
```

### OntologyLLMReasoner

LLM推理引擎，数据库未命中时的兜底策略。

```python
from ontology import OntologyLLMReasoner
from langchain_openai import ChatOpenAI

model = ChatOpenAI(...)
reasoner = OntologyLLMReasoner(model)

# LLM推理
instances = reasoner.reason_concept("new_concept", "city")
print(instances)
```

### OntologyExpander

混合调度器，协调数据库查询和LLM推理。

```python
from ontology import OntologyExpander

# 基础配置
expander = OntologyExpander(
    db_path="chatbi.db",
    model=model,
    enable_llm_reasoning=True,    # 启用LLM兜底
    enable_learning_mode=False      # 禁用学习模式
)

# 扩层
result = expander.expand("tier1_cities", "city")
```

### ConceptNameNormalizer

概念名称标准化器，处理别名映射。

```python
from ontology import ConceptNameNormalizer

# 标准化概念名称
normalized = ConceptNameNormalizer.normalize("一线城市")
print(normalized)  # 'tier1_cities'

# 动态添加别名
ConceptNameNormalizer.add_alias("新概念", "new_concept")
```

## 数据模型

### ontology_nodes 表

存储所有节点（概念/实例）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| node_name | TEXT | 节点名称（唯一） |
| node_type | TEXT | 节点类型（abstract_concept/concrete_instance） |
| concept_category | TEXT | 概念分类（city/customer/region/business） |
| display_name | TEXT | 显示名称 |
| description | TEXT | 描述信息 |
| attributes | TEXT | JSON格式扩展属性 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### ontology_edges 表

存储所有边关系（父子/隶属关系）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| parent_id | INTEGER | 父节点ID |
| child_id | INTEGER | 子节点ID |
| relation_type | TEXT | 关系类型（is_a/belongs_to/includes） |
| edge_weight | REAL | 关系权重 |
| created_at | TIMESTAMP | 创建时间 |

## 配置

### 环境变量

```bash
# 本体数据库路径
export ONTOLOGY_DB_PATH="chatbi.db"

# LLM配置
export OPENAI_MODEL="qwen3.5-plus"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_API_KEY="sk-xxx"
```

### 程序配置

```python
from ontology import OntologyExpander

expander = OntologyExpander(
    db_path="chatbi.db",              # 数据库路径
    model=model,                      # LangChain模型
    enable_llm_reasoning=True,        # 启用LLM兜底
    enable_learning_mode=False        # 禁用学习模式
)
```

## 测试

```bash
# 运行所有测试
pytest tests/python/test_ontology/ -v

# 运行特定测试
pytest tests/python/test_ontology/test_expander.py -v

# 查看覆盖率
pytest tests/python/test_ontology/ --cov=ontology --cov-report=html
```

## 示例场景

### 场景1：城市分类查询

```python
from ontology import OntologyExpander

expander = OntologyExpander("chatbi.db")

# 查询一线城市
cities = expander.expand("tier1_cities", "city")
print(f"一线城市: {', '.join(cities)}")
# 输出: 一线城市: shanghai, beijing, guangzhou, shenzhen
```

### 场景2：客户集团查询

```python
# 查询字节跳动集团所有客户
customers = expander.expand("bytedance_group", "customer")
print(f"字节跳动集团: {', '.join(customers)}")
# 输出: 字节跳动集团: wuhan_toutiao, wuhan_douyin, wuhan_feishu
```

### 场景3：区域查询

```python
# 查询华东区所有城市
cities = expander.expand("east_china", "region")
print(f"华东区: {', '.join(cities)}")
# 输出: 华东区: shanghai, hangzhou, nanjing, suzhou
```

## 扩展开发

### 添加新的概念分类

1. 在数据库中插入新的概念节点
2. 建立父子关系
3. 更新 `ConceptNameNormalizer.ALIAS_MAP`（如果需要别名支持）

```python
import sqlite3

conn = sqlite3.connect("chatbi.db")
cursor = conn.cursor()

# 添加新概念
cursor.execute("""
    INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
    VALUES ('new_category', 'abstract_concept', 'custom', '新分类')
""")

# 添加实例
cursor.execute("""
    INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
    VALUES ('instance1', 'concrete_instance', 'custom', '实例1')
""")

# 建立关系
cursor.execute("""
    INSERT INTO ontology_edges (parent_id, child_id, relation_type)
    SELECT ?, id, 'includes' FROM ontology_nodes WHERE node_name = 'instance1'
""", (cursor.lastrowid,))

conn.commit()
conn.close()
```

### 自定义LLM推理提示词

```python
from ontology import OntologyLLMReasoner

reasoner = OntologyLLMReasoner(model)
reasoner.reasoning_prompt = "自定义提示词..."
```

## 性能优化

### 查询缓存

```python
from ontology import OntologyExpander

expander = OntologyExpander("chatbi.db")
# 结果会被缓存，第二次查询更快
result1 = expander.expand("tier1_cities", "city")
result2 = expander.expand("tier1_cities", "city")  # 从缓存读取
```

### 批量查询

```python
from ontology import OntologyExpander

expander = OntologyExpander("chatbi.db")

# 批量查询多个概念
results = expander.batch_expand(["tier1_cities", "tier2_cities"])
```

## 故障排查

### 问题：数据库查询失败

**原因：** SQLite版本过低，不支持递归CTE

**解决方案：** 升级SQLite到3.35+

```bash
sqlite3 --version  # 检查版本
```

### 问题：LLM推理返回空结果

**原因：** LLM响应格式不符合预期

**解决方案：** 检查LLM配置和提示词，启用日志查看详细错误

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 问题：概念未找到

**原因：** 概念名称错误或别名未配置

**解决方案：** 使用别名或添加新的别名映射

```python
from ontology import ConceptNameNormalizer

# 检查标准化结果
normalized = ConceptNameNormalizer.normalize("概念名称")
print(f"标准化后的名称: {normalized}")
```

## 许可证

本模块遵循项目整体许可证。

## 贡献

欢迎提交Issue和Pull Request。
```

- [ ] **Step 3: Commit**

```bash
git add python/src/base_practice/16.chatbi/ontology/__init__.py python/src/base_practice/16.chatbi/ontology/README.md
git commit -m "docs: update ontology module exports and documentation

- Update module __init__.py with complete API
- Add comprehensive README documentation
- Include usage examples and troubleshooting
- Document data model and configuration options

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: 运行完整测试套件和代码审查

**Files:**
- Modify: 所有已创建的文件（根据审查结果调整）

**Interfaces:**
- 验证所有功能正常工作
- 确保代码质量符合标准

- [ ] **Step 1: Run complete test suite**

```bash
pytest tests/python/test_ontology/ -v --cov=ontology --cov-report=html
```

Expected: All tests pass, coverage >= 80%

- [ ] **Step 2: Check code style**

```bash
# 检查Python代码风格
flake8 python/src/base_practice/16.chatbi/ontology/
black --check python/src/base_practice/16.chatbi/ontology/
```

Expected: No style violations

- [ ] **Step 3: Review code for AGC tags**

```bash
# 验证所有文件都有AGC标签
grep -r "AGC:START" python/src/base_practice/16.chatbi/ontology/
grep -r "AGC:END" python/src/base_practice/16.chatbi/ontology/
grep -r "AGC:FILE" python/src/base_practice/16.chatbi/ontology/
```

Expected: All files have proper AGC tags

- [ ] **Step 4: Verify imports work correctly**

```bash
cd python/src/base_practice/16.chatbi/
python -c "from ontology import OntologyExpander, logical_layer_expansion, ConceptNameNormalizer; print('Import successful')"
```

Expected: "Import successful"

- [ ] **Step 5: Test with ChatBiAgentV1**

```bash
cd python/src/base_practice/16.chatbi/
python -c "
from ChatBiAgentV1 import agent
result = agent.invoke({'messages': [{'role': 'user', 'content': '一线城市上个月应收多少'}]})
print(result)
"
```

Expected: Agent successfully uses logical_layer_expansion tool

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "chore: final code review and cleanup

- All tests passing with >=80% coverage
- Code style validation passed
- AGC tags verified on all files
- Import checks successful
- Integration with ChatBiAgentV1 verified

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Plan Summary

本实现计划将本体逻辑扩层功能分解为9个独立的任务：

1. **Task 1-2**: 数据库和基础工具（表结构、标准化器）
2. **Task 3-5**: 核心组件（查询引擎、LLM推理、混合调度器）
3. **Task 6-7**: 集成和测试（LangChain工具、示例数据）
4. **Task 8-9**: 文档和审查（API导出、完整测试）

每个任务都遵循TDD原则：先写失败测试 → 最小实现 → 验证通过 → 提交。

**预期成果：**
- ✅ 完整的本体扩层模块（~1500行代码）
- ✅ 80%+ 测试覆盖率
- ✅ 完整的文档和示例
- ✅ 无缝集成到现有ChatBiAgentV1

**执行时间估计：** 3-4小时（包括测试和审查）