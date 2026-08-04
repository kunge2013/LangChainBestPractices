# 本体逻辑扩层功能设计文档

**项目名称:** ChatBI - 步骤3.3 逻辑扩层实现
**设计日期:** 2026-08-04
**版本:** v1.0

---

## 1. 概述

### 1.1 目标

实现ChatBI架构中步骤3.3"逻辑扩层"功能，将抽象业务概念扩展为具体实例名单，支持多类型概念扩层（城市分类、客户分类、区域分类、组合概念）。

### 1.2 核心需求

- ✅ 支持多类型概念扩层（城市/客户/区域/业务）
- ✅ 动态数据库存储 + LLM推理兜底（B+D策略）
- ✅ 先查数据库，未命中再LLM推理（策略A）
- ✅ 混合层级模式（不同概念类型不同层级深度）
- ✅ 基于SQLite递归CTE实现图结构（方案E）
- ✅ 可选学习模式（LLM推理结果回写数据库）

---

## 2. 系统架构

### 2.1 组件架构

```
┌─────────────────────────────────────────────────────────┐
│                    步骤3.3 逻辑扩层                      │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 本体存储层   │   │ 查询引擎层   │   │ LLM推理引擎  │
│ (SQLite图)   │   │(递归CTE查询) │   │  (兜底策略)  │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                   ┌──────────────┐
                   │ 混合调度器   │
                   │ (Ontology    │
                   │  Expander)   │
                   └──────────────┘
```

### 2.2 核心组件

#### 2.2.1 本体存储层（SQLite图结构）

**表结构：**
- `ontology_nodes`: 存储所有节点（概念/实例）
- `ontology_edges`: 存储所有边关系（父子/隶属关系）

**节点类型：**
- `abstract_concept`: 抽象概念（如"一线城市"、"字节跳动集团"）
- `concrete_instance`: 具体实例（如"上海"、"武汉今日头条"）

**关系类型：**
- `is_a`: 继承关系
- `belongs_to`: 隶属关系
- `includes`: 包含关系

#### 2.2.2 查询引擎层（OntologyQueryEngine）

**职责：**
- 封装递归CTE查询逻辑
- 支持多级扩层查询
- 支持类型过滤和返回格式控制

**核心方法：**
```python
def expand_concept(
    concept_name: str,
    max_level: int = None,
    return_type: str = "business_name"
) -> List[str]
```

#### 2.2.3 LLM推理引擎层（OntologyLLMReasoner）

**职责：**
- 数据库未命中时的兜底推理
- 支持上下文增强推理
- 可选结果回写数据库

**核心方法：**
```python
def reason_concept(
    concept_name: str,
    concept_category: str,
    context: Dict = None
) -> List[str]
```

#### 2.2.4 混合调度器（OntologyExpander）

**职责：**
- 协调数据库查询和LLM推理
- 实现B+D策略（动态数据库 + LLM兜底）
- 可选学习模式

**核心方法：**
```python
def expand(
    concept_name: str,
    concept_category: str = None,
    **kwargs
) -> List[str]
```

---

## 3. 数据模型设计

### 3.1 ontology_nodes 表

```sql
CREATE TABLE ontology_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL UNIQUE,           -- 节点名称（如"tier1_cities"）
    node_type TEXT NOT NULL,                  -- 节点类型：abstract_concept / concrete_instance
    concept_category TEXT NOT NULL,           -- 概念分类：city / customer / region / business
    display_name TEXT,                        -- 显示名称（中文名）
    description TEXT,                         -- 描述信息
    attributes TEXT,                          -- JSON格式扩展属性（如编码、层级）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_nodes_name ON ontology_nodes(node_name);
CREATE INDEX idx_nodes_type ON ontology_nodes(node_type);
CREATE INDEX idx_nodes_category ON ontology_nodes(concept_category);
```

**示例数据：**
```sql
-- 抽象概念
INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name)
VALUES
    ('tier1_cities', 'abstract_concept', 'city', '一线城市'),
    ('bytedance_group', 'abstract_concept', 'customer', '字节跳动集团'),
    ('east_china', 'abstract_concept', 'region', '华东区');

-- 具体实例
INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
VALUES
    ('shanghai', 'concrete_instance', 'city', '上海', '{"code": "021", "tier": "1"}'),
    ('beijing', 'concrete_instance', 'city', '北京', '{"code": "010", "tier": "1"}'),
    ('guangzhou', 'concrete_instance', 'city', '广州', '{"code": "020", "tier": "1"}');
```

### 3.2 ontology_edges 表

```sql
CREATE TABLE ontology_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL,               -- 父节点ID
    child_id INTEGER NOT NULL,                -- 子节点ID
    relation_type TEXT NOT NULL,              -- 关系类型：is_a / belongs_to / includes
    edge_weight REAL DEFAULT 1.0,             -- 关系权重
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES ontology_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (child_id) REFERENCES ontology_nodes(id) ON DELETE CASCADE,
    UNIQUE(parent_id, child_id, relation_type)
);

CREATE INDEX idx_edges_parent ON ontology_edges(parent_id);
CREATE INDEX idx_edges_child ON ontology_edges(child_id);
CREATE INDEX idx_edges_relation ON ontology_edges(relation_type);
CREATE INDEX idx_edges_parent_child ON ontology_edges(parent_id, child_id);
```

### 3.3 混合层级示例

#### 城市分类（两级结构）
```
tier1_cities (一线城市)
├── shanghai (上海)
├── beijing (北京)
├── guangzhou (广州)
└── shenzhen (深圳)
```

#### 客户分类（三级结构）
```
bytedance_group (字节跳动集团)
└── wuhan_subsidiaries (武汉子公司)
    ├── wuhan_toutiao (武汉今日头条)
    ├── wuhan_douyin (武汉抖音)
    └── wuhan_feishu (武汉飞书)
```

#### 区域分类（两级结构）
```
east_china (华东区)
├── jiangsu_province (江苏省)
│   ├── nanjing (南京)
│   └── suzhou (苏州)
├── zhejiang_province (浙江省)
│   ├── hangzhou (杭州)
│   └── ningbo (宁波)
└── shanghai_city (上海市)
    └── shanghai (上海)
```

---

## 4. 核心逻辑设计

### 4.1 递归CTE查询

```sql
-- 扩层查询：给定概念名，返回所有下级实例（支持多级）
WITH RECURSIVE expand_nodes AS (
    -- 基础查询：查找直接子节点
    SELECT
        child.id,
        child.node_name,
        child.node_type,
        child.display_name,
        1 AS level,
        child.id AS path_ids,
        child.node_name AS path_names
    FROM ontology_edges edge
    JOIN ontology_nodes child ON edge.child_id = child.id
    JOIN ontology_nodes parent ON edge.parent_id = parent.id
    WHERE parent.node_name = ?  -- 参数：概念名称

    UNION ALL

    -- 递归查询：查找子节点的子节点
    SELECT
        child.id,
        child.node_name,
        child.node_type,
        child.display_name,
        expand.level + 1,
        expand.path_ids || ',' || child.id,
        expand.path_names || ' > ' || child.node_name
    FROM ontology_edges edge
    JOIN ontology_nodes child ON edge.child_id = child.id
    JOIN expand_nodes expand ON edge.parent_id = expand.id
    WHERE expand.node_type = 'abstract_concept'  -- 只继续向下查找抽象概念
)
SELECT DISTINCT
    node_name,
    display_name,
    JSON_EXTRACT(attributes, '$.code') AS physical_code
FROM expand_nodes
WHERE node_type = 'concrete_instance'  -- 只返回具体实例
ORDER BY level, node_name;
```

### 4.2 扩层策略流程

```python
# 输入: concept_name = "tier1_cities"

# 步骤1：数据库查询
try:
    result = query_engine.expand_concept("tier1_cities")
    if result:
        return result  # 命中，返回 ["上海", "北京", "广州", "深圳"]
except Exception as e:
    logger.warning(f"数据库查询失败: {e}")

# 步骤2：LLM推理兜底
if enable_llm_reasoning:
    logger.info(f"数据库未命中，触发LLM推理: tier1_cities")
    result = llm_reasoner.reason_concept("tier1_cities", "city")
    # LLM推理: ["上海", "北京", "广州", "深圳"]

    # 步骤3：学习模式回写数据库
    if enable_learning_mode and result:
        _learn_from_reasoning("tier1_cities", result)

    return result

# 步骤4：返回空列表
return []
```

### 4.3 工具函数集成

```python
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
        - 输入: "tier1_cities" → 输出: ["上海", "北京", "广州", "深圳"]
        - 输入: "bytedance_group" → 输出: ["武汉今日头条", "武汉抖音", "武汉飞书"]
        - 输入: "east_china" → 输出: ["南京", "苏州", "杭州", "宁波", "上海"]

    参数:
        concept_name: 抽象概念名称
        concept_category: 概念分类（city/customer/region/business）
        return_type: 返回类型（business_name/physical_code/both）

    返回:
        具体实例的业务名称列表或物理编码列表
    """
    expander = OntologyExpander(
        db_path=DB_PATH,
        model=model,
        enable_llm_reasoning=True,
        enable_learning_mode=False
    )

    return expander.expand(concept_name, concept_category, return_type=return_type)
```

---

## 5. 错误处理策略

### 5.1 异常体系

```python
class OntologyExpansionError(Exception):
    """扩层异常基类"""
    pass

class ConceptNotFoundError(OntologyExpansionError):
    """概念未找到异常"""
    def __init__(self, concept_name: str):
        self.concept_name = concept_name
        super().__init__(f"概念 '{concept_name}' 未在数据库中找到")

class DatabaseQueryError(OntologyExpansionError):
    """数据库查询异常"""
    pass

class LLMReasoningError(OntologyExpansionError):
    """LLM推理异常"""
    pass
```

### 5.2 降级策略

1. **数据库查询失败** → 尝试LLM推理
2. **LLM推理也失败** → 返回空列表 + 告警
3. **概念未找到** → 返回相似概念建议

---

## 6. 性能优化

### 6.1 查询缓存

- 缓存扩层结果（TTL可配置，默认3600秒）
- 使用LRU缓存策略
- 支持手动清空缓存

### 6.2 批量查询

- 支持一次查询多个概念
- 使用线程池并行查询
- 减少数据库连接开销

### 6.3 数据库优化

- 复合索引：`idx_edges_parent_child`
- 定期VACUUM优化SQLite性能
- 使用事务批量写入

---

## 7. 边缘用例处理

### 7.1 概念名称歧义

- 别名映射表：`{"一线城市": "tier1_cities", "ByteDance": "bytedance_group"}`
- 模糊匹配支持（编辑距离）
- 大小写不敏感

### 7.2 空结果处理

- 策略1：返回空列表（静默失败）
- 策略2：抛出异常（让上层处理）
- 策略3：返回相似概念建议（交互式）

### 7.3 循环依赖检测

- 使用递归CTE检测图中的环
- 写入时预防循环依赖
- 检测到循环时告警

---

## 8. 测试策略

### 8.1 单元测试

- `TestOntologyQueryEngine`: 测试递归CTE查询
- `TestOntologyLLMReasoner`: 测试LLM推理（使用Mock）
- `TestOntologyExpander`: 测试混合调度逻辑

### 8.2 集成测试

- 端到端测试：完整扩层流程
- 数据库命中测试
- LLM兜底测试
- 学习模式测试

### 8.3 性能测试

- 单次查询响应时间 < 100ms
- 批量查询（10个概念）< 500ms
- 缓存命中率 > 80%

---

## 9. 监控与日志

### 9.1 指标收集

```python
@dataclass
class ExpansionMetrics:
    concept_name: str
    category: str
    source: str  # "database" | "llm" | "cache"
    duration_ms: float
    result_count: int
    timestamp: datetime
    success: bool
    error: str = None
```

### 9.2 统计指标

- 总扩层次数
- 成功率
- 平均响应时间
- 数据库命中率
- LLM兜底率
- 平均返回结果数量

---

## 10. 学习模式实现

### 10.1 回写策略

```python
def _learn_from_reasoning(self, concept_name: str, instances: List[str]):
    """
    学习模式：将LLM推理结果回写数据库

    步骤：
    1. 创建新的抽象概念节点
    2. 为每个实例创建节点（如果不存在）
    3. 建立父子关系
    """
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    try:
        # 1. 创建抽象概念节点
        cursor.execute("""
            INSERT OR IGNORE INTO ontology_nodes
            (node_name, node_type, concept_category, display_name)
            VALUES (?, 'abstract_concept', ?, ?)
        """, (concept_name, self._infer_category(concept_name), concept_name))

        concept_id = cursor.lastrowid

        # 2. 为每个实例创建节点并建立关系
        for instance_name in instances:
            # 创建实例节点
            cursor.execute("""
                INSERT OR IGNORE INTO ontology_nodes
                (node_name, node_type, concept_category, display_name)
                VALUES (?, 'concrete_instance', ?, ?)
            """, (instance_name, self._infer_category(concept_name), instance_name))

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

### 10.2 配置选项

- `enable_learning_mode`: 是否启用学习模式
- `llm_confidence_threshold`: LLM推理置信度阈值（低于此值不回写）
- `auto_approve_new_concepts`: 是否自动批准新概念

---

## 11. 集成到现有系统

### 11.1 更新 ChatBiAgentV1.py

```python
# 在工具列表中添加
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
```

### 11.2 更新 System Prompt

添加步骤2：调用 `logical_layer_expansion` 进行逻辑扩层

### 11.3 示例执行流程

```python
# 用户输入: "一线城市上个月营收"

# 步骤1：实体抽取
entities = extract_entities_enhanced("一线城市上个月营收")
# → {location: "一线城市", metric: "应收", time: "上个月"}

# 步骤2：逻辑扩层
instances = logical_layer_expansion("tier1_cities", "city")
# → ["上海", "北京", "广州", "深圳"]

# 步骤3：映射到客户ID
customer_ids = [ENTITY_TO_ID.get(city) for city in instances]
# → ["CUST_SH_001", "CUST_BJ_002", ...]

# 步骤4-8：后续SQL生成和执行...
```

---

## 12. 技术栈

- **数据库**: SQLite 3.35+（支持递归CTE）
- **LLM**: OpenAI / Qwen 3.5 Plus
- **Python**: 3.12+
- **并发**: concurrent.futures
- **缓存**: functools.lru_cache
- **日志**: Python logging

---

## 13. 后续优化方向

1. **图数据库集成**: 当本体规模增长到百万级时，迁移到Neo4j
2. **实时同步**: 与业务系统实时同步本体数据
3. **推理优化**: 使用向量数据库加速相似概念检索
4. **可视化**: 提供本体图谱可视化界面
5. **权限控制**: 不同角色的本体读写权限管理

---

## 14. 附录

### 14.1 数据库初始化脚本

```sql
-- 创建表结构（见上文）

-- 插入初始数据
INSERT INTO ontology_nodes (node_name, node_type, concept_category, display_name, attributes)
VALUES
    -- 城市分类
    ('tier1_cities', 'abstract_concept', 'city', '一线城市', NULL),
    ('shanghai', 'concrete_instance', 'city', '上海', '{"code": "021"}'),
    ('beijing', 'concrete_instance', 'city', '北京', '{"code": "010"}'),
    ('guangzhou', 'concrete_instance', 'city', '广州', '{"code": "020"}'),
    ('shenzhen', 'concrete_instance', 'city', '深圳', '{"code": "0755"}'),
    -- 客户分类
    ('bytedance_group', 'abstract_concept', 'customer', '字节跳动集团', NULL),
    ('wuhan_subsidiaries', 'abstract_concept', 'customer', '武汉子公司', NULL),
    ('wuhan_toutiao', 'concrete_instance', 'customer', '武汉今日头条', NULL),
    ('wuhan_douyin', 'concrete_instance', 'customer', '武汉抖音', NULL),
    ('wuhan_feishu', 'concrete_instance', 'customer', '武汉飞书', NULL);

-- 建立关系
INSERT INTO ontology_edges (parent_id, child_id, relation_type)
SELECT
    (SELECT id FROM ontology_nodes WHERE node_name = 'tier1_cities'),
    (SELECT id FROM ontology_nodes WHERE node_name = 'shanghai'),
    'includes'
UNION ALL
-- ... 其他关系
```

### 14.2 配置示例

```python
# config.py
ONTOLOGY_CONFIG = {
    "db_path": "chatbi.db",
    "enable_llm_reasoning": True,
    "enable_learning_mode": False,
    "cache_ttl": 3600,
    "llm_confidence_threshold": 0.8,
    "max_expansion_level": None,
}
```

---

**文档结束**