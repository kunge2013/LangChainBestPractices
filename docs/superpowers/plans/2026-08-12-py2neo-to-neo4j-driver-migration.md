# py2neo → 官方 neo4j 驱动迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use kunge2013:subagent-driven-development (recommended) or kunge2013:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 QASystemOnMedicalKG 模块的 py2neo 依赖替换为官方 neo4j Python 驱动。

**Architecture:** 新建 `neo4j_conn.py` 共享连接模块(懒加载单例 driver + `get_session()` 上下文管理器),将 `build_medicalgraph.py` 和 `answer_search.py` 中的 py2neo API 替换为官方驱动调用,保持业务逻辑和 Cypher 语句不变。

**Tech Stack:** Python 3.12+, neo4j (official driver) >=5.0,<6.0, python-dotenv

**Spec:** `docs/superpowers/specs/2026-08-12-py2neo-to-neo4j-driver-migration-design.md`

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/neo4j_conn.py` | Create | 共享 Neo4j 连接模块(单例 driver + session 工厂) |
| `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/build_medicalgraph.py` | Modify | 移除 py2neo,Node 创建改为 Cypher CREATE,g.run 改为 session.run |
| `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/answer_search.py` | Modify | 移除 py2neo,g.run 改为 session.run |
| `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/requirements.txt` | Modify | py2neo → neo4j |
| `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/tests/test_neo4j_conn.py` | Create | neo4j_conn 模块单元测试 |

---

### Task 1: 创建 neo4j_conn.py 共享连接模块

**Files:**
- Create: `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/neo4j_conn.py`
- Test: `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/tests/test_neo4j_conn.py`

- [ ] **Step 1: 写失败测试**

创建 `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/tests/__init__.py`(空文件)。

创建 `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/tests/test_neo4j_conn.py`:

```python
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-12
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# [AGC:START] tool=Cc author=fangkun
class TestGetSession:
    """测试 get_session 上下文管理器"""

    @patch("neo4j_conn.GraphDatabase")
    def test_get_session_returns_session_context(self, mock_gdb):
        from neo4j_conn import get_session

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        with get_session() as session:
            assert session is mock_session

        mock_gdb.driver.assert_called_once()
    # [AGC:END]

    # [AGC:START] tool=Cc author=fangkun
    @patch("neo4j_conn.GraphDatabase")
    def test_driver_is_singleton(self, mock_gdb):
        import neo4j_conn

        neo4j_conn._driver = None
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        with patch.dict(os.environ, {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "test",
            "NEO4J_DATABASE": "neo4j",
        }):
            with neo4j_conn.get_session():
                pass
            with neo4j_conn.get_session():
                pass

        assert mock_gdb.driver.call_count == 1
        neo4j_conn._driver = None
    # [AGC:END]

    # [AGC:START] tool=Cc author=fangkun
    @patch("neo4j_conn.GraphDatabase")
    def test_session_uses_database_from_env(self, mock_gdb):
        import neo4j_conn

        neo4j_conn._driver = None
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        with patch.dict(os.environ, {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "test",
            "NEO4J_DATABASE": "mydb",
        }):
            with neo4j_conn.get_session():
                pass

        mock_driver.session.assert_called_with(database="mydb")
        neo4j_conn._driver = None
    # [AGC:END]


# [AGC:START] tool=Cc author=fangkun
class TestCloseDriver:
    """测试 close_driver 函数"""

    @patch("neo4j_conn.GraphDatabase")
    def test_close_driver_closes_and_resets(self, mock_gdb):
        import neo4j_conn

        mock_driver = MagicMock()
        neo4j_conn._driver = mock_driver

        neo4j_conn.close_driver()

        mock_driver.close.assert_called_once()
        assert neo4j_conn._driver is None
    # [AGC:END]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
conda activate langchain11
python -m pytest tests/test_neo4j_conn.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'neo4j_conn'`

- [ ] **Step 3: 实现 neo4j_conn.py**

创建 `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/neo4j_conn.py`:

```python
# [AGC:FILE] tool=Cc author=fangkun date=2026-08-12
import os
from contextlib import contextmanager

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(override=True)

_driver = None


# [AGC:START] tool=Cc author=fangkun
def _get_driver():
    """懒加载并返回 Neo4j driver 单例。"""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "")
        username = os.getenv("NEO4J_USERNAME", "")
        password = os.getenv("NEO4J_PASSWORD", "")
        _driver = GraphDatabase.driver(uri, auth=(username, password))
    return _driver
# [AGC:END]


# [AGC:START] tool=Cc author=fangkun
@contextmanager
def get_session():
    """获取 Neo4j session 的上下文管理器。"""
    driver = _get_driver()
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    session = driver.session(database=database)
    try:
        yield session
    finally:
        session.close()
# [AGC:END]


# [AGC:START] tool=Cc author=fangkun
def close_driver():
    """关闭 driver 并重置单例。"""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
# [AGC:END]
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -m pytest tests/test_neo4j_conn.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
cd "D:/github.io/LangChainBestPractices"
git add "python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/neo4j_conn.py" \
        "python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/tests/__init__.py" \
        "python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/tests/test_neo4j_conn.py"
git commit -m "feat: add neo4j_conn shared connection module"
```

---

### Task 2: 更新 requirements.txt

**Files:**
- Modify: `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/requirements.txt`

- [ ] **Step 1: 替换 py2neo 为 neo4j**

在 `requirements.txt` 中,将:

```
py2neo==2021.2.4
```

替换为:

```
neo4j>=5.0,<6.0
```

- [ ] **Step 2: 安装新依赖**

```bash
conda activate langchain11
pip install "neo4j>=5.0,<6.0"
```

Expected: 安装成功,无错误。

- [ ] **Step 3: 确认 py2neo 不再需要**

```bash
pip show py2neo
```

Expected: 仍可能显示已安装(不影响),但代码中不再 import。如需卸载可执行 `pip uninstall py2neo -y`。

- [ ] **Step 4: 提交**

```bash
cd "D:/github.io/LangChainBestPractices"
git add "python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/requirements.txt"
git commit -m "chore: replace py2neo with official neo4j driver in requirements"
```

---

### Task 3: 迁移 build_medicalgraph.py

**Files:**
- Modify: `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/build_medicalgraph.py`

- [ ] **Step 1: 修改导入部分(第 7-11 行)**

将:

```python
import os
import json
from py2neo import Graph,Node
from dotenv import load_dotenv
load_dotenv(override=True)
```

替换为:

```python
import os
import json
from neo4j_conn import get_session
```

- [ ] **Step 2: 修改 __init__(第 13-16 行)**

将:

```python
    def __init__(self):
        cur_dir = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        self.data_path = os.path.join(cur_dir, 'data/medical.json')
        self.g = Graph(os.getenv("NEO4J_URI", ""),auth=(os.getenv("NEO4J_USERNAME", ""), os.getenv("NEO4J_PASSWORD", "")),name=os.getenv("NEO4J_DATABASE", ""))
```

替换为:

```python
    def __init__(self):
        cur_dir = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        self.data_path = os.path.join(cur_dir, 'data/medical.json')
```

- [ ] **Step 3: 修改 create_node 方法(第 156-163 行)**

将:

```python
    '''建立节点'''
    def create_node(self, label, nodes):
        count = 0
        for node_name in nodes:
            node = Node(label, name=node_name)
            self.g.create(node)
            count += 1
            print(count, len(nodes))
        return
```

替换为:

```python
    '''建立节点'''
    # [AGC:START] tool=Cc author=fangkun
    def create_node(self, label, nodes):
        count = 0
        with get_session() as session:
            for node_name in nodes:
                session.run(
                    f"CREATE (n:`{label}` {{name: $name}})",
                    name=node_name,
                )
                count += 1
                print(count, len(nodes))
        return
    # [AGC:END]
```

- [ ] **Step 4: 修改 create_diseases_nodes 方法(第 166-177 行)**

将:

```python
    '''创建知识图谱中心疾病的节点'''
    def create_diseases_nodes(self, disease_infos):
        count = 0
        for disease_dict in disease_infos:
            node = Node("Disease", name=disease_dict['name'], desc=disease_dict['desc'],
                        prevent=disease_dict['prevent'] ,cause=disease_dict['cause'],
                        easy_get=disease_dict['easy_get'],cure_lasttime=disease_dict['cure_lasttime'],
                        cure_department=disease_dict['cure_department']
                        ,cure_way=disease_dict['cure_way'] , cured_prob=disease_dict['cured_prob'])
            self.g.create(node)
            count += 1
            print(count)
        return
```

替换为:

```python
    '''创建知识图谱中心疾病的节点'''
    # [AGC:START] tool=Cc author=fangkun
    def create_diseases_nodes(self, disease_infos):
        count = 0
        with get_session() as session:
            for disease_dict in disease_infos:
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
                count += 1
                print(count)
        return
    # [AGC:END]
```

- [ ] **Step 5: 修改 create_relationship 方法中的 g.run(第 227 行)**

在 `create_relationship` 方法中,将:

```python
            try:
                self.g.run(query)
                count += 1
                print(rel_type, count, all)
            except Exception as e:
                print(e)
```

替换为:

```python
            # [AGC:START] tool=Cc author=fangkun
            try:
                with get_session() as session:
                    session.run(query)
                count += 1
                print(rel_type, count, all)
            except Exception as e:
                print(e)
            # [AGC:END]
```

注意:方法内其余代码(去重逻辑、query 字符串拼接)保持不变。

- [ ] **Step 6: 语法验证**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -c "import ast; ast.parse(open('build_medicalgraph.py', encoding='utf-8').read()); print('Syntax OK')"
```

Expected: `Syntax OK`

- [ ] **Step 7: 导入验证**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -c "from build_medicalgraph import MedicalGraph; print('Import OK')"
```

Expected: `Import OK`(需要 neo4j 和 dotenv 已安装,.env 文件存在)

- [ ] **Step 8: 确认无 py2neo 残留**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -c "
import ast, sys
tree = ast.parse(open('build_medicalgraph.py', encoding='utf-8').read())
imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
for node in imports:
    if isinstance(node, ast.ImportFrom):
        print(f'from {node.module} import ...')
    else:
        for alias in node.names:
            print(f'import {alias.name}')
"
```

Expected: 输出中不包含 `py2neo`。

- [ ] **Step 9: 提交**

```bash
cd "D:/github.io/LangChainBestPractices"
git add "python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/build_medicalgraph.py"
git commit -m "refactor: migrate build_medicalgraph.py from py2neo to neo4j driver"
```

---

### Task 4: 迁移 answer_search.py

**Files:**
- Modify: `python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/answer_search.py`

- [ ] **Step 1: 修改导入部分(第 7-10 行)**

将:

```python
from py2neo import Graph
import os
from dotenv import load_dotenv
load_dotenv(override=True)
```

替换为:

```python
from neo4j_conn import get_session
```

注意:删除 `import os`(该文件中不再使用 os)。

- [ ] **Step 2: 修改 __init__(第 12-16 行)**

将:

```python
    def __init__(self):
        self.g = Graph(os.getenv("NEO4J_URI", ""),
                       auth=(os.getenv("NEO4J_USERNAME", ""), os.getenv("NEO4J_PASSWORD", "")),
                       name=os.getenv("NEO4J_DATABASE", ""))
        self.num_limit = 20
```

替换为:

```python
    def __init__(self):
        self.num_limit = 20
```

- [ ] **Step 3: 修改 search_main 方法(第 18-30 行)**

将:

```python
    '''执行cypher查询，并返回相应结果'''
    def search_main(self, sqls):
        final_answers = []
        for sql_ in sqls:
            question_type = sql_['question_type']
            queries = sql_['sql']
            answers = []
            for query in queries:
                ress = self.g.run(query).data()
                answers += ress
            final_answer = self.answer_prettify(question_type, answers)
            if final_answer:
                final_answers.append(final_answer)
        return final_answers
```

替换为:

```python
    '''执行cypher查询，并返回相应结果'''
    # [AGC:START] tool=Cc author=fangkun
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
    # [AGC:END]
```

注意:`answer_prettify` 方法保持不变。

- [ ] **Step 4: 语法验证**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -c "import ast; ast.parse(open('answer_search.py', encoding='utf-8').read()); print('Syntax OK')"
```

Expected: `Syntax OK`

- [ ] **Step 5: 导入验证**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -c "from answer_search import AnswerSearcher; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 6: 确认无 py2neo 残留**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
grep -n "py2neo\|self\.g" answer_search.py; echo "EXIT:$?"
```

Expected: `EXIT:1`(无匹配)

- [ ] **Step 7: 提交**

```bash
cd "D:/github.io/LangChainBestPractices"
git add "python/src/base_practice/18.graph_rag/QASystemOnMedicalKG/answer_search.py"
git commit -m "refactor: migrate answer_search.py from py2neo to neo4j driver"
```

---

### Task 5: 整体验证

**Files:**
- Verify: all files in QASystemOnMedicalKG/

- [ ] **Step 1: 确认全模块无 py2neo 引用**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
grep -rn "py2neo" --include="*.py" .
```

Expected: 无输出(除 tests/ 目录中可能有 mock 字符串,但不应有实际 import)

- [ ] **Step 2: 验证所有模块可导入**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -c "
from neo4j_conn import get_session, close_driver
from build_medicalgraph import MedicalGraph
from answer_search import AnswerSearcher
from question_classifier import QuestionClassifier
from question_parser import QuestionPaser
print('All imports OK')
"
```

Expected: `All imports OK`(question_classifier 加载词典可能需要几秒)

- [ ] **Step 3: 运行全部单元测试**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -m pytest tests/ -v
```

Expected: 4 tests PASS

- [ ] **Step 4: 验证 chatbot_graph 可实例化**

```bash
cd "D:/github.io/LangChainBestPractices/python/src/base_practice/18.graph_rag/QASystemOnMedicalKG"
python -c "
from chatbot_graph import ChatBotGraph
bot = ChatBotGraph()
print('ChatBotGraph instantiation OK')
"
```

Expected: `ChatBotGraph instantiation OK`(需要 .env 配置正确且 Neo4j 可连接)

- [ ] **Step 5: 最终提交(如有遗漏修复)**

```bash
cd "D:/github.io/LangChainBestPractices"
git status
```

如有未提交的变更,add 并 commit。
