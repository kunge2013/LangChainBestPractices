# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
# 本体逻辑扩层模块

## 概述

本模块实现ChatBI架构中步骤3.3"逻辑扩层"功能，将抽象业务概念扩展为具体实例名单。

## 功能特性

- 支持多类型概念扩层（城市/客户/区域/业务）
- 混合层级模式（不同概念类型不同层级深度）
- 动态数据库存储 + LLM推理兜底
- 概念名称标准化（别名映射）
- 可选学习模式（LLM推理结果回写数据库）
- 基于SQLite递归CTE实现图结构

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
result = logical_layer_expansion.invoke({
    "concept_name": "tier1_cities",
    "concept_category": "city"
})
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
