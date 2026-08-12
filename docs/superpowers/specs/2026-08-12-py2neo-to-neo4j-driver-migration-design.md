# py2neo → 官方 neo4j 驱动迁移设计

**日期**: 2026-08-12
**模块**: `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/`
**范围**: 将 py2neo 替换为官方 `neo4j` Python 驱动

## 背景

QASystemOnMedicalKG 模块当前使用 `py2neo==2021.2.4` 连接 Neo4j。同目录下的 `kg_builder/0.neo4j-kg-builder.py` 已使用官方 `neo4j` 驱动。为统一技术栈、减少依赖,需将 py2neo 迁移到官方驱动。

py2neo 仅在两个文件中使用:
- `build_medicalgraph.py` — 图谱构建(节点和关系创建)
- `answer_search.py` — 问答查询(Cypher 执行)

## 目标

- 移除 `py2neo` 依赖,改用官方 `neo4j` 驱动
- 保持所有业务逻辑和现有 Cypher 语句不变
- 抽取共享连接模块,避免重复代码

## 非目标

- 不修改 Cypher 查询语句(包括 question_parser.py 中生成的 Cypher)
- 不重构业务逻辑
- 不做批量插入优化
- 不引入新的抽象层(如 py2neo 兼容包装)

## 方案选型

选择**方案 A:直接 Cypher 替换**。

- py2neo 的 `Node(label, **props)` + `graph.create(node)` 是 OGM 风格,官方驱动无对等 API,需用 Cypher `CREATE` 语句替代
- `graph.run(query).data()` 在官方驱动中几乎完全一致:`session.run(query).data()`
- 不引入包装层,直接使用官方驱动标准用法

## 详细设计

### 1. 新建 `neo4j_conn.py`

共享连接模块,位于 QASystemOnMedicalKG 目录下。

**职责**:
- 模块加载时执行 `load_dotenv(override=True)`
- 懒加载全局单例 `_driver`(`GraphDatabase.driver(uri, auth=(u,p))`)
- 提供 `get_session()` 上下文管理器,自动使用 `NEO4J_DATABASE` 环境变量
- 提供 `close_driver()` 用于关闭连接

**接口**:

```python
from neo4j_conn import get_session, close_driver

with get_session() as session:
    result = session.run("MATCH (n) RETURN n LIMIT 1")
    records = result.data()
```

**环境变量**(与现有 example.env 一致):
- `NEO4J_URI` — bolt URI
- `NEO4J_USERNAME` — 用户名
- `NEO4J_PASSWORD` — 密码
- `NEO4J_DATABASE` — 数据库名(默认 neo4j)

### 2. 修改 `build_medicalgraph.py`

**导入变更**:

```python
# 删除
from py2neo import Graph, Node

# 新增
from neo4j_conn import get_session
```

**`__init__` 变更**:
- 删除 `self.g = Graph(...)` 行
- 保留 `self.data_path` 设置
- 删除该文件中的 `load_dotenv(override=True)` 调用(已由 neo4j_conn 统一处理)

**`create_node` 方法变更**(原第 156-163 行):

py2neo:
```python
node = Node(label, name=node_name)
self.g.create(node)
```

neo4j:
```python
with get_session() as session:
    session.run(
        f"CREATE (n:`{label}` {{name: $name}})",
        name=node_name,
    )
```

标签名无法参数化(Cypher 限制),使用 f-string;属性值 `$name` 参数化。

**`create_diseases_nodes` 方法变更**(原第 166-177 行):

py2neo:
```python
node = Node("Disease", name=d['name'], desc=d['desc'],
            prevent=d['prevent'], cause=d['cause'],
            easy_get=d['easy_get'], cure_lasttime=d['cure_lasttime'],
            cure_department=d['cure_department'],
            cure_way=d['cure_way'], cured_prob=d['cured_prob'])
self.g.create(node)
```

neo4j:
```python
with get_session() as session:
    session.run(
        "CREATE (n:Disease {name: $name, desc: $desc, prevent: $prevent, "
        "cause: $cause, easy_get: $easy_get, cure_lasttime: $cure_lasttime, "
        "cure_department: $cure_department, cure_way: $cure_way, "
        "cured_prob: $cured_prob})",
        name=disease_dict['name'],
        desc=disease_dict['desc'],
        prevent=disease_dict['prevent'],
        cause=disease_dict['cause'],
        easy_get=disease_dict['easy_get'],
        cure_lasttime=disease_dict['cure_lasttime'],
        cure_department=disease_dict['cure_department'],
        cure_way=disease_dict['cure_way'],
        cured_prob=disease_dict['cured_prob'],
    )
```

显式传递 9 个属性,与原 Node 构造完全一致。`cure_department` 和 `cure_way` 是列表类型,Neo4j 原生支持。

**`create_relationship` 方法变更**(原第 213-232 行):

仅将 `self.g.run(query)` 替换为:
```python
with get_session() as session:
    session.run(query)
```

Cypher 字符串(含字符串拼接)保持不变。

### 3. 修改 `answer_search.py`

**导入变更**:

```python
# 删除
from py2neo import Graph

# 新增
from neo4j_conn import get_session
```

**`__init__` 变更**:
- 删除 `self.g = Graph(...)` 行
- 保留 `self.num_limit = 20`
- 删除该文件中的 `load_dotenv(override=True)` 调用

**`search_main` 方法变更**(原第 18-30 行):

将查询循环包裹在单个 session 中:

```python
def search_main(self, sqls):
    final_answers = []
    with get_session() as session:
        for sql_ in sqls:
            question_type = sql_['question_type']
            queries = sql_['sql']
            answers = []
            for query in queries:
                ress = session.run(query).data()
                answers += ress
            final_answer = self.answer_prettify(question_type, answers)
            if final_answer:
                final_answers.append(final_answer)
    return final_answers
```

`session.run(query).data()` 返回 `list[dict]`,与 py2neo 的 `g.run(query).data()` 格式完全一致,因此 `answer_prettify` 方法零改动。

### 4. 修改 `requirements.txt`

- 删除:`py2neo==2021.2.4`
- 新增:`neo4j>=5.0,<6.0`

### 5. 不修改的文件

| 文件 | 原因 |
|------|------|
| `question_classifier.py` | 不涉及数据库连接 |
| `question_parser.py` | 仅生成 Cypher 字符串,不执行 |
| `chatbot_graph.py` | 仅组合三个子模块,无直接数据库调用 |
| `prepare_data/build_data.py` | 通过 `MedicalGraph()` 间接使用,自动生效 |
| `prepare_data/data_spider.py` | 不涉及数据库 |
| `prepare_data/max_cut.py` | 不涉及数据库 |

## API 映射总结

| py2neo | neo4j 官方驱动 |
|--------|---------------|
| `Graph(uri, auth=(u,p), name=db)` | `GraphDatabase.driver(uri, auth=(u,p))` + `driver.session(database=db)` |
| `Node(label, **props)` + `g.create(node)` | `session.run("CREATE (n:Label {...})", **params)` |
| `g.run(query).data()` | `session.run(query).data()` |

## 风险与注意事项

1. **driver 生命周期**:官方驱动的 driver 是长生命周期对象,session 是短生命周期的。共享模块使用单例 driver,每个操作创建独立 session。
2. **标签参数化**:Cypher 不支持参数化标签名,`create_node` 中标签来自代码内部(非用户输入),使用 f-string 安全。
3. **列表属性**:`cure_department` 和 `cure_way` 是 Python 列表,neo4j 驱动自动将其映射为 Neo4j 列表类型。
4. **`data()` 返回值**:两个驱动的 `.data()` 方法均返回 `list[dict]`,键名为 Cypher RETURN 子句中的别名(如 `m.name`),无需调整 answer_prettify。
