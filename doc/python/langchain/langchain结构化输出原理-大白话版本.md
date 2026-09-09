---
title: "LangChain 结构化输出原理 - 费曼笔记（大白话版）"
date: 2026-09-09
description: "用大白话理解 LangChain 结构化输出原理：请求体三块并列（messages/tools/tool_choice）、函数调用协议、模型为什么返回 JSON；按三套代码循序渐进——多文件版 → 单文件版 → 原生 Python 版"
category: [LangChain]
tags: [费曼笔记, 学习笔记, LangChain, 结构化输出, function_calling, tool_choice, tools, JSON]
lang: zh
draft: false
---

# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
# LangChain 结构化输出原理 - 大白话版

> 配套代码：[python/src/structured_output](https://github.com/kunge2013/LangChainBestPractices/tree/main/python/src/structured_output)
>
> 本文按**三套代码循序渐进**，每套代码是一大块章节，同一套原理、三种写法，越往后越接近本质：

| 大块 | 代码版本 | 文件 | 为什么先/后看它 |
|---|---|---|---|
| **大块一** | LangChain 多文件版 | `pipeline.py` / `extractors.py` / `schemas.py` / `observability.py` / `config.py` / `demo.py` | 生产用法，分层最清晰，先看懂每一层负责什么 |
| **大块二** | LangChain 单文件版 | `simple_onefile.py` | 同一套逻辑平铺在一个文件里，去掉了跨文件抽象，方便逐段对照 |
| **大块三** | 原生 Python 版 | `pure_structured_output.py` | 只用标准库 urllib 直连接口，把「发给模型的请求体」逐字节摊开，看本质 |

---

## 一、一句话说明白

**结构化输出 = 让大模型把你说的话，填进一张"规定好的表"里交回来。**

平时的大模型像一个"随口聊天的朋友"，你问什么它自由回答；
开了结构化输出，它像一个"必须按表格填的前台"，说的话被硬塞进固定格式，方便电脑读取。

**三个关键词先记住，全文围绕它们展开：**

| 关键词 | 大白话 | 通俗比喻 |
|---|---|---|
| **提示词（messages / content）** | 你说的话 | 病人的口头描述 |
| **tools** | 规定好的"空表"（表格清单） | 前台桌上印好格子的病历表 |
| **tool_choice** | 命令大模型"必须填这张表"的死命令 | 服务员"就点这道菜，别的不要" |

---

## 二、大白话故事：去诊所看病，要填一张病历表

想象你生病去诊所，整个过程是这样的：

1. **你说话**：告诉前台"我头疼、发烧，两天了"。
2. **前台有一张病历表**：上面印好了格子——姓名、年龄、症状、风险等级（低/中/高）。
3. **前台按规矩填表**：把你的话填进对应格子，不闲聊、不写别的。
4. **填好的表交给你**：一张整整齐齐的病历表。
5. **你检查**：姓名填了吗？年龄是不是数字？有没有填错栏？不对就让她重填。
6. **存进电脑**：这张表以后就能被电脑自动处理。

**"结构化输出"就是这件事**——让大模型（前台）把你说的话，填进一张"规定好的表"里交回来。

```mermaid
---
title: "结构化输出 = 诊所填表流水线"
---
flowchart LR
    A["你：一句话<br/>(输入)"] --> B["打包成一个大包裹<br/>(请求体)"]
    B --> C["大模型<br/>(前台)"]
    C --> D["填好的表<br/>(JSON 输出)"]
    D --> E["检查表对不对<br/>(校验)"]
    E --> F["存进电脑<br/>(Python 数据)"]
```

---

## 三、核心原理：请求体 = 三块并列的大包裹

**这一节是整篇文章的"地基"，三套代码都是同一个原理的不同写法。先把它立起来。**

普通聊天时，发给大模型的包裹里**只有你说的一句话**。
结构化输出时，包裹里**多出两块东西**，和你说的话**并排**放在一起：

```mermaid
---
title: "请求体 = 三块并列的大包裹"
---
flowchart LR
    subgraph 包裹["📦 请求体（发给模型的一个大包裹）"]
        A["① 你说的话<br/>messages"]
        B["② 空表清单<br/>tools"]
        C["③ 死命令<br/>tool_choice"]
    end
    A ~~~ B ~~~ C
    style 包裹 fill:#fafafa,stroke:#616161
    style A fill:#e3f2fd,stroke:#1565c0
    style B fill:#e8f5e9,stroke:#388e3c
    style C fill:#fff3e0,stroke:#f57c00
```

**注意"并排"两个字，这是全文最关键的认知：**

- 三块字段是**平级的**，谁也不在谁里面。
- `tools` 和 `tool_choice` 不塞进你说的话里，而是和你说的话**平行**放在请求体顶层。
- 正因为它们平行，才会出现"提示词一个字没改，模型却也看到了表格"。

真实发给模型的请求体长这样（三块并列，请盯住 `messages` / `tools` / `tool_choice`）：

```json
{
  "model": "glm-5.2",
  "messages": [
    {"role": "user", "content": "患者张三，32岁，因发热咳嗽就诊……"}
  ],
  "temperature": 0.7,
  "max_tokens": 20000,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "PatientRecord",
        "description": "自由文本 -> 结构化病历抽取的演示 Schema。",
        "parameters": {
          "type": "object",
          "additionalProperties": false,
          "required": ["name", "age", "symptoms", "risk_level"],
          "properties": {
            "name":       {"type": "string"},
            "age":        {"type": "integer"},
            "symptoms":   {"type": "array", "items": {"type": "string"}},
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "contact":    {"type": ["object", "null"],
                           "properties": {"email": {"type": ["string", "null"]},
                                          "phone": {"type": ["string", "null"]}}}
          }
        }
      }
    }
  ],
  "tool_choice": {"type": "function", "function": {"name": "PatientRecord"}}
}
```

### 3.1 拆开第一块：messages = 提示词（你说的话）

`messages` 就是你打给大模型的那句话，里面装着你要处理的信息。`content` 是其中每条消息的文本。

```
患者张三，32岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13800000000。
```

> **关键认知**：在 function_calling 通道下，这句提示词**从头到尾一个字都没被改**。
> 表格（schema）不是拼接在这句话后面的，而是走另一条通道（`tools`）平行送进去的。这就是"提示词零改动"。

### 3.2 拆开第二块：tools = 空表清单

`tools` 里装的，是你要大模型照着填的"空表"。它告诉大模型：**有这些表格可以用**。

```json
{
  "type": "function",
  "function": {
    "name": "PatientRecord",                  // 表的名字：病历表
    "description": "自由文本 -> 结构化病历抽取", // 这表干嘛用的
    "parameters": {                           // 表上印了哪些格子
      "type": "object",
      "required": ["name", "age", "symptoms", "risk_level"],  // 必须填的格子
      "properties": {
        "name":       {"type": "string"},                 // 姓名：填文字
        "age":        {"type": "integer"},                // 年龄：填数字
        "symptoms":   {"type": "array", "items": {"type": "string"}},  // 症状：一串文字
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]}, // 只能三选一
        "contact":    {"type": ["object", "null"]}        // 可填可不填
      }
    }
  }
}
```

> 注意"风险等级"那一格写着 `enum: low / medium / high`——意思是**只能从这三个里挑一个**，
> 不许自己发明一个 "SEVERE"。这就是表格在管着大模型。

这张表不是手写的，而是**从一个 Python 类（Pydantic `BaseModel`）自动生成的**——大块一会展开。

### 3.3 拆开第三块：tool_choice = 死命令

光给大模型一张表还不够——它可能偷懒，不交填好的表，反而像聊天一样随便说两句。
所以还要下一条**命令**：**你必须用这张表！**

```json
{
  "type": "function",
  "function": {"name": "PatientRecord"}
}
```

```mermaid
---
title: "tools vs tool_choice 类比：菜单 vs 点菜"
---
flowchart LR
    subgraph 技术概念["💻 技术概念"]
        A["tools<br/>空表清单（菜单）"]
        B["tool_choice<br/>死命令（点菜）"]
    end
    subgraph 现实类比["🌍 现实类比"]
        C["📋 菜单上有好多菜<br/>但都没端上来"]
        D["👨‍🍳 服务员下单<br/>：就做这道，别的不做"]
    end
    A <-->|"映射"| C
    B <-->|"映射"| D
    style 技术概念 fill:#e3f2fd,stroke:#1565c0
    style 现实类比 fill:#e8f5e9,stroke:#388e3c
```

**三块连起来一句话记住：**

| 字段 | 大白话 | 负责什么 |
|---|---|---|
| messages（提示词） | 你说的话 | 提供信息 |
| tools | 空表清单（菜单） | 告诉大模型"要填这张表" |
| tool_choice | 死命令（点菜） | 锁死大模型必须填表，不许闲聊 |

### 3.4 原理一：模型为什么"看到"了表格？（tools 通道）

最常见的疑问：**模型知道需要哪些字段，是提示词里写了什么？还是它继承了 Python 的 BaseModel？**
——**两个答案都不对。** 完整链路是这样：

```mermaid
flowchart TB
    P["🐍 Pydantic 类<br/>PatientRecord"] --> JS["📄 JSON Schema<br/>model_json_schema()"]
    JS --> T["🧰 tools[].function.parameters<br/>+ tool_choice"]
    T --> POST["📤 HTTP POST /chat/completions"]
    POST --> TOKEN["🔤 推理服务把 tools 转成<br/>「特殊工具令牌」"]
    TOKEN --> MODEL["🧠 追加进模型的输入上下文"]
    MODEL --> KNOW["模型「读到」字段名/类型/required/enum<br/>——只是不在你写的聊天文本里"]

    style POST fill:#fff3e0,stroke:#f57c00
    style MODEL fill:#e3f2fd,stroke:#1565c0
    style KNOW fill:#c8e6c9,stroke:#2e7d32
```

1. **"继承了 BaseModel" 只是客户端侧的 Python 类型安全**。它让 `model_json_schema()` 能产出
   schema、让 `model_validate()` 能校验结果。它**不会**让模型知道任何东西——模型只知道协议层
   送进去的 token。`BaseModel` 在链路两端各用一次：前头产出 schema 喂给 API，后头校验返回结果；
   中间只有纯 JSON 往返，没有 Python 对象。
2. **"提示词层面处理"也不是主因**。function_calling 通道下，你写的 `messages` 文本**一个字都没变**。
   schema 是走 `tools` 通道**平行**送进去的，所以才有"提示词零改动"。
3. 推理服务收到请求后，会把 `tools` 里每个函数的 name/description/parameters **转成特殊工具令牌，
   追加进模型的输入上下文**（和 messages 一起）。所以模型**确实读到了** `PatientRecord` 的全部字段
   ——只是它不在你写的聊天文本里。

> 反过来说：如果你不发 `tools`（比如 json_mode 通道），模型输入上下文里**没有任何字段定义**，
> 模型根本不知道 `PatientRecord` 长什么样，你必须把 schema 文本**自己写进提示词**。

### 3.5 原理二：模型为什么"返回 JSON"？（函数调用协议）

即使模型"看到"了表格，它凭什么输出合法 JSON？答案在**工具调用协议的输出格式**：

1. `tool_choice` 强制模型**必须发起一次对 `PatientRecord` 的工具调用**，不能自由发挥聊天文本。
2. 工具调用协议的输出格式规定：`tool_calls[].function.arguments` **必须是一个符合该函数
   `parameters` schema 的 JSON 字符串**。
3. 模型在训练（指令微调 + 工具调用数据）时**内化了这个契约**。

于是模型返回长这样：

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_xxx",
        "type": "function",
        "function": {
          "name": "PatientRecord",
          "arguments": "{\"name\":\"张三\",\"age\":32,\"symptoms\":[\"发热\",\"咳嗽\"],\"risk_level\":\"high\"}"
        }
      }]
    }
  }]
}
```

**重点看 `arguments` 这个字段**：它是一整个**字符串**，里面是符合 schema 的 JSON。

```mermaid
---
title: "函数调用 = 前台填表交回"
---
flowchart LR
    subgraph 模型侧["🧠 模型"]
        A["被 tool_choice 强制<br/>发起工具调用"]
        B["tool_calls[0].function.arguments<br/>= JSON 字符串"]
    end
    subgraph 前台侧["🏥 前台"]
        C["被命令：必须填表"]
        D["arguments 就是填好的表<br/>（JSON 文本）"]
    end
    A --> B
    C --> D
    style 模型侧 fill:#e3f2fd,stroke:#1565c0
    style 前台侧 fill:#e8f5e9,stroke:#388e3c
```

**"返回 JSON"是协议输出格式的必然结果**，不是模型即兴发挥。
但这是**条件概率**：模型仍可能填错枚举（`risk_level: "SEVERE"`）、漏必填字段（`name` 缺失）、
把数字输出成字符串（`age: "32"`）。所以协议只保证"**是** JSON、大体符合 schema"——
**是否符合你的 schema，最终防线永远在你自己的校验层**。

> 这是整篇文章最重要的一句话：
> **模型侧尽力而为（协议只保证"是 JSON"），校验层是硬保证（符不符合你的表由你兜底）。**

### 3.6 两条返回通道：tool_calls 和 content

模型返回 JSON 有两条通道，取决于你用哪种 `method`：

| method | JSON 从哪拿 | 说明 |
|---|---|---|
| `function_calling` | `tool_calls[0].function.arguments` | 强制工具调用，schema 走 tools 通道，提示词零改动 |
| `json_mode` | `content`（文本） | 只要求"输出合法 JSON"，schema 要自己写进 prompt |

所以**客户端取 JSON 的代码**要两个都找：先看 `tool_calls`，没有再退到 `content`。

---

## 四、大块一：LangChain 多文件版（先看最完整的分层）

**这一版是生产用法，按职责拆成几个小文件，每一层只干一件事。** 先看懂每层负责什么，
后面两个版本就是把它"压扁"和"去壳"。

### 4.1 文件地图

```mermaid
flowchart LR
    subgraph 入口["🎬 入口"]
        DEMO["demo.py<br/>怎么跑、选 Fake 还是 Real"]
    end
    subgraph 五层["🧩 五层保证"]
        S["① schemas.py<br/>数据模型（表长什么样）"]
        E["② extractors.py<br/>生成层（唯一的模型入口）"]
        P["③ pipeline.py<br/>校验+修复+兜底闭环"]
        O["④ observability.py<br/>JSONL 日志 + 失败计数"]
        C["⑤ config.py<br/>Provider 配置"]
    end
    DEMO --> S & E & P & O & C
    E --> P
    P --> O
    style 入口 fill:#fff3e0,stroke:#f57c00
    style 五层 fill:#e3f2fd,stroke:#1565c0
```

| 文件 | 角色 | 大白话 |
|---|---|---|
| [schemas.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/schemas.py) | 数据模型 | 规定"病历表"长什么样 |
| [config.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/config.py) | 配置 | 告诉程序用哪个模型、走哪个接口 |
| [extractors.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/extractors.py) | 生成层 | 唯一碰模型的地方：把 prompt 变成 JSON 字符串 |
| [pipeline.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/pipeline.py) | 闭环核心 | 生成 → 校验 → 重试 → 兜底 |
| [observability.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/observability.py) | 观测 | 记日志、数失败率 |
| [demo.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/demo.py) | 入口 | 演示怎么跑、选假模型还是真模型 |

### 4.2 ① 数据模型：schemas.py —— 表长什么样

```python
# [AGC:START] tool=Cc author=fangkun
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class RiskLevel(str, Enum):
    """枚举字段：模型输出 "SEVERE" 这类非法取值会触发校验失败。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ContactInfo(BaseModel):
    """嵌套模型：演示对象嵌套校验。"""
    model_config = ConfigDict(extra="forbid")
    email: str | None = None
    phone: str | None = None

class PatientRecord(BaseModel):
    """自由文本 -> 结构化病历抽取的演示 Schema。"""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(strict=True)
    age: int = Field(strict=True)
    symptoms: list[str]
    risk_level: RiskLevel
    contact: ContactInfo | None = None
# [AGC:END]
```

**逐行翻译成表格**（每个 Python 元素变成发给模型的什么）：

| Pydantic 元素 | JSON Schema 产物 | 是否发给模型 |
|---|---|---|
| `class PatientRecord` | `function.name = "PatientRecord"` | ✓ |
| 类 docstring | `function.description` | ✓ |
| `ConfigDict(extra="forbid")` | `additionalProperties: false`（多输出字段即非法） | ✓ |
| `name: str` / `age: int` | `"type": "string"` / `"integer"` | ✓ |
| `symptoms: list[str]` | `"type":"array","items":{"type":"string"}` | ✓ |
| `risk_level: RiskLevel` | `"enum": ["low","medium","high"]` | ✓ |
| `contact: ContactInfo \| None = None` | `"anyOf":[...,{"type":"null"}]` | ✓ |
| 必填字段 name/age/symptoms/risk_level | `parameters.required` | ✓ |
| `Field(strict=True)` | **无**——strict 只影响客户端校验 | ✗ |

> 两个容易误会的点：
> 1. **`strict=True` 不会发给模型**。它只影响你自己这边用 `model_validate()` 校验时要不要严格转换
>    类型，是"本地执法"，不是"模型约束"。
> 2. **`extra="forbid"` 会发给模型**。它变成 `additionalProperties: false`，意思是"表格上没有的
>    栏不许填"——模型多输出一个字段都算失败。

### 4.3 ② 生成层：extractors.py —— 唯一碰模型的地方

生成层把「模型输出」规范化为「JSON 字符串」，供后面的校验层用。**它假装自己是假的也行**——
`FakeExtractor` 离线模拟四种行为，让整个闭环不需要 API key 就能演示。

```python
# [AGC:START] tool=Cc author=fangkun
from dataclasses import dataclass
from langchain_core.messages import BaseMessage

@dataclass
class RawResult:
    """抽取结果：json_str 为可解析的 JSON 字符串；为空时 note 说明原因。"""
    json_str: str | None
    note: str = ""
    raw_message: dict | None = None

class RealExtractor:
    """用 LangChain 1.x 的 with_structured_output() 产出结构化响应。"""

    def __init__(self, llm: BaseChatModel, schema: type[BaseModel], method: str) -> None:
        self.method = method
        # include_raw=True：保留原始消息，由本包自己负责最终严格校验
        self._runnable = llm.with_structured_output(schema, method=method, include_raw=True)

    def extract(self, text: str) -> RawResult:
        res: dict[str, Any] = self._runnable.invoke(text)
        raw: BaseMessage | None = res.get("raw")
        if raw is None:
            return RawResult(None, "无原始输出", None)
        json_str, note = self._pick_json(raw)
        return RawResult(json_str, note, _serialize_message(raw))

    @staticmethod
    def _pick_json(raw: BaseMessage) -> tuple[str | None, str]:
        """从 AIMessage 里提取 JSON：function_calling 取 tool_calls[0].args，否则取 content。"""
        tool_calls = getattr(raw, "tool_calls", None)
        if tool_calls:
            args = tool_calls[0].get("args") if isinstance(tool_calls[0], dict) else None
            if isinstance(args, dict) and args:
                return json.dumps(args, ensure_ascii=False), ""
        content = getattr(raw, "content", None)
        if isinstance(content, str) and content.strip():
            body = _strip_json(content)
            if body:
                return body, ""
            return None, "content 中未找到 JSON 对象"
        return None, "模型未返回工具调用或文本内容"
# [AGC:END]
```

**大白话翻译 `_pick_json`（对应 §3.6 的两条返回通道）：**

1. 先看模型的输出里有没有 `tool_calls`（走了函数调用通道）→ 有就把 `arguments` 里的 JSON 拿出来。
2. 没有就看看 `content`（走了文本通道）→ 有就抠出 JSON。
3. 两个都没有 → 返回失败说明，交给后面的重试。

**`with_structured_output(schema, method=method, include_raw=True)` 一句话讲透：**

- `with_structured_output` 是 LangChain 1.x 的首选 API：一条调用同时完成「把 Pydantic 类转成 schema 塞进 tools」+「强制 tool_choice」+「解析返回」。
- `include_raw=True`：**保留原始 AIMessage**，让校验权握在自己手里，而不是让框架解析完只给你一个实例。

### 4.4 ③ 闭环核心：pipeline.py —— 生成 → 校验 → 重试 → 兜底

这是"最小可靠闭环"的心脏。**模型是概率机器，会填错，所以必须有一层层的检查与补救。**

```mermaid
flowchart TD
    S([开始]) --> T["输入文本 text"]
    T --> L{"attempt <= max_retries + 1 ?"}
    L -- "否" --> FB["兜底层：返回 fallback<br/>(默认 None) + 记日志 + 失败计数"]
    FB --> E([结束])
    L -- "是" --> G["生成层：extractor.extract()<br/>with_structured_output / JSON mode"]
    G --> A{"语法层：<br/>json.loads 可解析？"}
    A -- "失败" --> R["记录 retry 日志<br/>FIX_TEMPLATE 把错误喂回 prompt"]
    R --> L
    A -- "成功" --> V{"Schema 层：<br/>Pydantic 严格校验"}
    V -- "失败" --> R
    V -- "通过" --> OK["返回 schema 实例<br/>记 ok 日志 + 成功计数"]
    OK --> E
```

```python
# [AGC:START] tool=Cc author=fangkun
FIX_TEMPLATE = (
    "\n\n【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】\n{error}"
)

class StructuredOutputPipeline:
    """把任意『文本 -> JSON 字符串』抽取器包装成带保证的闭环。"""

    def __init__(self, extractor, schema, *, max_retries=2, fallback=None,
                 logger=None, counter=None, provider="unknown", model="unknown", method="unknown"):
        self.extractor = extractor
        self.schema = schema
        self.max_retries = max_retries
        self.fallback = fallback               # 兜底实例；默认 None
        self.logger = logger or JsonlLogger()
        self.counter = counter or FailureCounter()
        self._meta = {"provider": provider, "model": model, "method": method}

    def invoke(self, text: str) -> tuple[BaseModel | None, Attempt]:
        request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        errors: list[str] = []
        last_prompt, last_raw = text, RawResult(None, "")

        for attempt in range(1, self.max_retries + 2):
            prompt = text if attempt == 1 else text + FIX_TEMPLATE.format(error=errors[-1])
            last_prompt, last_raw = prompt, self.extractor.extract(prompt)
            try:
                obj = self._validate(last_raw)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                self._emit(request_id, attempt, "retry", errors[-1], last_prompt, last_raw, None)
                continue
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.counter.record(ok=True, attempts_used=attempt)
            self._emit(request_id, attempt, "ok", "", last_prompt, last_raw, obj.model_dump())
            return obj, Attempt(request_id, "ok", attempt, errors, latency_ms)

        latency_ms = int((time.perf_counter() - started) * 1000)
        self.counter.record(ok=False, attempts_used=self.max_retries + 1)
        last = errors[-1] if errors else "重试耗尽"
        self._emit(request_id, self.max_retries + 1, "fallback", last, last_prompt, last_raw, None)
        return self.fallback, Attempt(request_id, "fallback", self.max_retries + 1, errors, latency_ms)

    def _validate(self, raw: RawResult) -> BaseModel:
        """语法层 + schema 层：缺 JSON / 解析失败 / Pydantic 严格校验失败都抛错。"""
        if not raw.json_str:
            raise ValueError(raw.note or "模型未返回可解析的 JSON")
        data = json.loads(raw.json_str)                       # 语法层
        return self.schema.model_validate(data)               # schema 层
# [AGC:END]
```

**五层保证逐一解释：**

| 层 | 大白话 | 代码位置 | 失败后果 |
|---|---|---|---|
| ① 数据模型 | 规定"表"长什么样 | [schemas.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/schemas.py) | —— |
| ② 生成层 | 唯一碰模型：把 prompt 变成 JSON 字符串 | [extractors.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/extractors.py) | 产出 `RawResult(None, 原因)` |
| ③ 校验层 | `json.loads`（语法层）+ `model_validate`（schema 层） | [pipeline.py:_validate](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/pipeline.py) | 抛错 → 进入重试 |
| ④ 修复层 | 把校验错误喂回 prompt，让模型自纠正 | `FIX_TEMPLATE` | 重试次数可配 |
| ⑤ 兜底+观测 | 重试耗尽返回 None；JSONL 日志 + 失败计数 | [pipeline.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/pipeline.py) + [observability.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/observability.py) | 宁缺毋滥 |

**为什么重试真能救回失败？** 有一次真实观测：attempt=1 模型回了纯文本澄清（没走 tool call）→
语法层拦截 `ValueError: content 中未找到 JSON 对象`；attempt=2 带上这条错误重发，模型这次乖乖
输出合法 JSON。**重试不是撞运气，而是把失败原因变成了下一轮的有效输入。**

```mermaid
---
title: "重试 = 把错误批注退回给前台"
---
flowchart LR
    subgraph 第一次["第一次"]
        A["📝 原始文本"] --> B["🤖 模型输出坏 JSON"]
    end
    subgraph 第二次["第二次"]
        C["📝 原始文本 + 错误批注<br/>「root.age: 类型应为 integer，实际 str」"]
        D["🤖 模型针对性修正"]
    end
    B -->|"校验拦截"| C
    style 第一次 fill:#ffcdd2,stroke:#c62828
    style 第二次 fill:#c8e6c9,stroke:#2e7d32
```

### 4.5 ④ 观测：observability.py —— 让失败可见

纯标准库，不需要任何云端 key 也能常开。每次调用写一条 JSONL + 进程内失败率计数。

```python
# [AGC:START] tool=Cc author=fangkun
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "logs" / "structured_output.jsonl"

class JsonlLogger:
    """以 append 方式写 JSONL，一次调用写一条，避免多进程互相覆盖。"""
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.environ.get("STRUCTURED_OUTPUT_LOG", DEFAULT_LOG_PATH))

    def log(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

class FailureCounter:
    """进程内指标：总调用 / 成功 / 最终失败 / 重试次数。"""
    def __init__(self) -> None:
        self.total = 0; self.ok = 0; self.failed = 0; self.retries_used = 0

    def record(self, *, ok: bool, attempts_used: int) -> None:
        self.total += 1
        self.retries_used += attempts_used - 1
        if ok: self.ok += 1
        else: self.failed += 1

    def summary(self) -> dict[str, Any]:
        rate = (self.ok / self.total * 100.0) if self.total else 0.0
        return {"total": self.total, "ok": self.ok, "failed": self.failed,
                "retries_used": self.retries_used, "success_rate_%": round(rate, 2)}
# [AGC:END]
```

一条日志长这样（完整轨迹：完整 prompt / 原始 JSON / 错误 / 解析结果）：

```json
{"ts": "2026-09-09T14:01:50+0800", "request_id": "bfc4573d9bc0", "status": "retry",
 "attempt": 1, "max_retries": 2,
 "error": "ValueError: content 中未找到 JSON 对象",
 "prompt": "一个发烧的病人。",
 "raw_json": null,
 "parsed": null,
 "provider": "deepseek", "model": "deepseek-v4-flash", "method": "function_calling"}
```

### 4.6 ⑤ Provider 配置：config.py —— 两个模型的坑都在这里

deepseek 和 qwen 都走 OpenAI 兼容接口，用 `ChatOpenAI` 统一建模。**最大的坑是 qwen 的 thinking 模式**：

- qwen 系列**默认开启 thinking**，thinking 模式下 API 只允许 `tool_choice="auto"`，而结构化输出
  强制指定工具 → 触发 400 错误。
- **解法：显式关闭 thinking** `extra_body={"enable_thinking": False}`。

```python
# [AGC:START] tool=Cc author=fangkun
# [config.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/config.py)
from langchain_openai import ChatOpenAI

PROVIDERS: dict[str, dict[str, Any]] = {
    "qwen": {
        "base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "model": "qwen3.6-plus",
        # qwen 系列默认开启 thinking，会限制 tool_choice 导致结构化输出 400 错误，必须显式关闭
        "extra_body": {"enable_thinking": False},
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "extra_body": None,
    },
}

def build_chat_model(provider: str = "auto") -> ChatOpenAI:
    """构建指向 OpenAI 兼容接口的 ChatOpenAI；env 变量可覆盖 provider 默认值。"""
    name = resolve_provider(provider)
    cfg = PROVIDERS[name]
    max_tokens = os.environ.get("OPENAI_MAX_TOKENS")
    return ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", cfg["model"]),
        base_url=os.environ.get("OPENAI_BASE_URL", cfg["base_url"]),
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0")),
        max_tokens=int(max_tokens) if max_tokens else None,
        **(cfg["extra_body"] or {}),
    )
# [AGC:END]
```

> ⚠️ **版本坑**：langchain-openai **1.4+ 的 `with_structured_output` 不传 `method` 时，默认已是
> `json_schema`**（不再是 0.x 的 `function_calling`）。而 `json_schema` 严格模式仅
> OpenAI/Claude/Gemini 支持，deepseek/qwen 收到会直接 400。**deepseek/qwen 必须显式传
> `method="function_calling"`（最稳）或 `"json_mode"`。**

### 4.7 ⑥ 入口：demo.py —— 怎么跑

demo.py 最重要的作用是演示「怎么切换 Fake / Real」：**生产/测试切换 = 换构造函数的实参**，
pipeline 内部零改动。

```python
# [AGC:START] tool=Cc author=fangkun
def run_fake_demo() -> None:
    """四种脚本化行为，完整演示成功 / 自修复 / 兜底 / 无 JSON 四条路径。"""
    for mode in ("good", "retry_once", "hopeless", "nojson"):
        counter = FailureCounter()
        pipeline = StructuredOutputPipeline(
            FakeExtractor(mode), PatientRecord,
            max_retries=2, logger=JsonlLogger(), counter=counter,
            provider="fake", model=f"fake:{mode}", method="fake",
        )
        print(f"\n############ 假模型模式：{mode} ############")
        for label, text in SAMPLE_TEXTS.items():
            _run_case(pipeline, label, text)
        print(f"\n计数: {counter.summary()}")

def run_real_demo(provider: str, method: str) -> None:
    """真实调用：走 with_structured_output + 校验 / 重试 / 兜底闭环。"""
    cfg = PROVIDERS[resolve_provider(provider)]
    llm = build_chat_model(provider)
    pipeline = StructuredOutputPipeline(
        RealExtractor(llm, PatientRecord, method), PatientRecord,
        max_retries=2, logger=JsonlLogger(), counter=FailureCounter(),
        provider=resolve_provider(provider), model=cfg["model"], method=method,
    )
    for label, text in SAMPLE_TEXTS.items():
        _run_case(pipeline, label, text)
# [AGC:END]
```

**运行命令：**

```bash
# 离线演示（无需 API key）：四种假模型剧本
cd python && python -m src.structured_output.demo --fake

# 离线自检（验证真实 extractor 能构造）
python -m src.structured_output.demo --self-check

# 真实调用
python -m src.structured_output.demo --provider qwen --method function_calling
python -m src.structured_output.demo --provider deepseek --method json_mode
```

**四种假模型剧本**（`FakeExtractor` 离线模拟，跑通闭环所有分支）：

| 剧本 | 模拟的失败形态 | 闭环行为 | 结果 |
|---|---|---|---|
| `good` | 模型正常 | 1 次成功 | `ok, attempts=1` |
| `retry_once` | 缺必填 + 类型错 + 枚举非法 | 第 1 次失败 → 错误喂回 → 第 2 次成功 | `ok, attempts=2` |
| `hopeless` | 永远输出坏 JSON | 重试 2 次仍失败 → 兜底 | `fallback, None` |
| `nojson` | 返回纯文本（无 JSON） | 语法层失败 → 重试 → 兜底 | `fallback, None` |

---

## 五、大块二：LangChain 单文件版（同一套逻辑，平铺一个文件）

**这一版把大块一的多文件逻辑压缩到一个文件 `simple_onefile.py`**，去掉跨文件抽象，
五层保证从上到下平铺，注释最细——非常适合对照着读懂"每一层到底干了什么"。

### 5.1 和大块一的关系

```mermaid
---
title: "多文件版 → 单文件版"
---
flowchart LR
    subgraph 多文件["📁 多文件版（大块一）"]
        A1["schemas.py"]
        A2["extractors.py"]
        A3["pipeline.py"]
        A4["observability.py"]
        A5["config.py"]
    end
    subgraph 单文件["📄 单文件版（大块二）"]
        B1["simple_onefile.py<br/>五层平铺：①数据模型 ②生成层<br/>③校验层 ④修复层+兜底 ⑤入口"]
    end
    A1 & A2 & A3 & A4 & A5 --> B1
    style 多文件 fill:#e3f2fd,stroke:#1565c0
    style 单文件 fill:#e8f5e9,stroke:#388e3c
```

### 5.2 完整代码（逐段讲解）

**① 数据模型：和 `schemas.py` 一模一样** —— 表长什么样，三套代码完全一致。

```python
# [AGC:START] tool=Cc author=fangkun
# ═════════════════════════════════════════════════════════════════
# ① 数据模型：模型要输出的结构。
#    类名 -> function.name；类 docstring -> function.description；
#    字段类型 -> JSON Schema type；枚举 -> enum；| None -> anyOf(..., null)。
#    extra="forbid" -> additionalProperties:false（模型多输出字段即判失败）
#    Field(strict=True) 只影响客户端校验，不会发给模型。
# ═════════════════════════════════════════════════════════════════
class RiskLevel(str, Enum):
    """枚举字段：模型输出 "SEVERE" 这类非法取值会触发校验失败。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ContactInfo(BaseModel):
    """嵌套模型：演示对象嵌套校验。"""
    model_config = ConfigDict(extra="forbid")
    email: str | None = None
    phone: str | None = None

class PatientRecord(BaseModel):
    """自由文本 -> 结构化病历抽取的演示 Schema。"""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(strict=True)
    age: int = Field(strict=True)
    symptoms: list[str]
    risk_level: RiskLevel
    contact: ContactInfo | None = None
# [AGC:END]
```

**② 生成层：`extract_real`** —— 和大块一 `RealExtractor._pick_json` 是同一段逻辑，
只是这里平铺成普通函数。关键还是 `with_structured_output(method=..., include_raw=True)`，
取 JSON 依然「先看 `tool_calls`，再退 `content`」。

```python
# [AGC:START] tool=Cc author=fangkun
def _strip_json(content: str) -> str | None:
    """从文本里抠出第一个 JSON 对象，容忍 ```json 围栏和前导文本。"""
    text = content.strip()
    if text.startswith("```"):
        first, last = text.find("\n"), text.rfind("```")
        if first != -1 and last != -1 and last > first:
            text = text[first + 1:last].strip()
    s, e = text.find("{"), text.rfind("}")
    return text[s:e + 1] if s != -1 and e != -1 and e > s else None

def extract_real(text: str, llm: Any) -> RawResult:
    """真实路径：with_structured_output(include_raw=True) 保留原始消息。
    JSON 从 tool_calls[0].args（function_calling）或 content（json_mode）里取。"""
    res = llm.invoke(text)
    raw = res.get("raw")
    if raw is None:
        return RawResult(None, "无原始输出")
    tc = getattr(raw, "tool_calls", None)
    if tc:
        args = tc[0].get("args") if isinstance(tc[0], dict) else None
        if isinstance(args, dict) and args:
            return RawResult(json.dumps(args, ensure_ascii=False))
    content = getattr(raw, "content", None)
    if isinstance(content, str) and content.strip():
        body = _strip_json(content)
        if body:
            return RawResult(body)
        return RawResult(None, "content 中未找到 JSON 对象")
    return RawResult(None, "模型未返回工具调用或文本内容")
# [AGC:END]
```

**③ 校验层：`validate`** —— 语法层 `json.loads` + Schema 层 Pydantic 严格校验，
任何一层失败都抛错交给重试。

```python
# [AGC:START] tool=Cc author=fangkun
def validate(raw: RawResult, schema: type[BaseModel]) -> BaseModel:
    if not raw.json_str:
        raise ValueError(raw.note or "模型未返回可解析的 JSON")
    data = json.loads(raw.json_str)      # 语法层
    return schema.model_validate(data)   # Schema 层（strict 由 Field 控制）
# [AGC:END]
```

**④ 修复层 + ⑤ 兜底层：`run_pipeline`** —— 与 `pipeline.py` 的 `invoke` 完全同构。
注意这里刻意演示了「观测与流程解耦」：流程里只把日志**攒成变量**（纯数据，不碰 IO），
流程结束后才**统一落盘**。

```python
# [AGC:START] tool=Cc author=fangkun
FIX_TEMPLATE = "\n\n【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】\n{error}"

def run_pipeline(text: str, extract, schema: type[BaseModel], *,
                 max_retries: int = 2, fallback: BaseModel | None = None):
    """返回 (解析结果 | fallback, 实际尝试次数, 错误列表, 日志记录列表)。"""
    errors: list[str] = []
    records: list[dict] = []              # 日志先攒在这，流程跑完再统一写出
    last_prompt, last_raw = text, RawResult(None, "")
    for attempt in range(1, max_retries + 2):
        # attempt=1 用原始文本；重试则追加错误反馈（修复层）
        last_prompt = text if attempt == 1 else text + FIX_TEMPLATE.format(error=errors[-1])
        last_raw = extract(last_prompt)
        try:
            obj = validate(last_raw, schema)
        except (json.JSONDecodeError, ValueError) as exc:   # 语法层 / Schema 层失败
            errors.append(f"{type(exc).__name__}: {exc}")
            records.append(_record(attempt, "retry", last_prompt, last_raw, None, errors[-1]))
            continue
        records.append(_record(attempt, "ok", last_prompt, last_raw, obj.model_dump(), ""))
        write_records(records)            # 流程结束，统一落盘
        return obj, attempt, errors, records
    # 重试耗尽：兜底层（fallback 可配置，默认 None）
    last = errors[-1] if errors else "重试耗尽"
    records.append(_record(max_retries + 1, "fallback", last_prompt, last_raw, None, last))
    write_records(records)                # 流程结束，统一落盘
    return fallback, max_retries + 1, errors, records

def _record(attempt: int, status: str, prompt: str, raw: RawResult,
            parsed: dict | None, error: str) -> dict:
    """单条日志 = 纯数据（不碰 IO）：完整 prompt / 原始 JSON / 解析结果 / 错误。"""
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "request_id": uuid.uuid4().hex[:12],
        "status": status, "attempt": attempt, "error": error[:400],
        "prompt": prompt, "raw_json": raw.json_str, "parsed": parsed,
    }

def write_records(records: list[dict]) -> None:
    """把攒好的日志统一写入 JSONL：IO 与流程完全分离。"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
# [AGC:END]
```

**⑥ 入口：`build_llm` + `main`** —— 关键坑在注释里：**必须显式传 `method="function_calling"`**，
因为 langchain-openai 1.4+ 默认已是 `json_schema`（deepseek/qwen 会 400）。

```python
# [AGC:START] tool=Cc author=fangkun
def build_llm() -> ChatOpenAI:
    base_url = os.environ.get("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
    model = os.environ.get("OPENAI_MODEL", "qwen3.6-plus")
    # qwen 默认开 thinking，会限制 tool_choice 导致结构化输出 400，必须显式关
    extra = {"enable_thinking": False} if ("dashscope" in base_url or "qwen" in model.lower()) else None
    return ChatOpenAI(model=model, base_url=base_url,
                      api_key=os.environ.get("OPENAI_API_KEY"),
                      temperature=0, **(extra or {}))

def main() -> None:
    load_dotenv(override=True)
    # 必须显式传 method：langchain-openai 1.4+ 默认已是 json_schema（仅 OpenAI/Claude/Gemini
    # 支持），deepseek/qwen 不传会 400。function_calling 对二者最稳。
    llm = build_llm().with_structured_output(PatientRecord, method="function_calling", include_raw=True)
    extract = lambda t: extract_real(t, llm)

    for label, text in SAMPLES.items():
        print(f"\n=== {label} ===")
        obj, attempt, errors, records = run_pipeline(text, extract, PatientRecord, max_retries=2)
        print(f"attempts={attempt}  结果={obj.model_dump() if obj else None}")
        for err in errors:
            print(f"  [err] {err[:160]}")
# [AGC:END]
```

### 5.3 运行命令

```bash
cd python && python -m src.structured_output.simple_onefile
```

> **读懂这一版的价值**：你看到了 `schemas` / `extractors` / `pipeline` / `observability` 之间的
> 调用关系全部摊开在一个文件里。接下来大块三要做的，就是**把 LangChain 这层壳也脱掉**，
> 直接看请求体本身。

---

## 六、大块三：原生 Python 版（摊开请求体，看本质）

**这一版用纯标准库 `urllib` 直连 OpenAI 兼容接口，完全不依赖 LangChain。**
它把「发给模型的请求体」逐字节摊开在眼前——正是 §三 讲的原理原样可见，
让你彻底看清：`tools` / `tool_choice` 到底是怎么被拼进请求体的。

```mermaid
---
title: "单文件版 → 原生 Python 版"
---
flowchart LR
    subgraph LangChain版["🤖 LangChain 版"]
        B1["LangChain 帮你拼请求体<br/>with_structured_output()"]
    end
    subgraph 原生版["🔧 原生 Python 版"]
        C1["urllib 手拼请求体<br/>json.dumps(payload) POST"]
    end
    B1 -->|"脱掉框架这层壳"| C1
    style LangChain版 fill:#e3f2fd,stroke:#1565c0
    style 原生版 fill:#e8f5e9,stroke:#388e3c
```

### 6.1 手写 SCHEMA：把 Pydantic 类翻译成纯 dict

这里不写 Pydantic 类，直接手写等价于 `PatientRecord.model_json_schema()` 的 dict：

```python
# [AGC:START] tool=Cc author=fangkun
SCHEMA = {
    "name": "PatientRecord",
    "description": "自由文本 -> 结构化病历抽取的演示 Schema。",
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "age", "symptoms", "risk_level"],
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "symptoms": {"type": "array", "items": {"type": "string"}},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "contact": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "email": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
            },
        },
    },
}
# [AGC:END]
```

**对照 §三 的请求体 JSON**：`SCHEMA` 正是被塞进 `tools[].function.parameters` 的那一坨。

#### SCHEMA 的旅程：什么时候用到、会不会给大模型

先直接回答：**会。每次请求都发给大模型。** 而且 SCHEMA 在整条链路里**用了两次**——
前头当"约束"发给模型，后头当"裁判"校验结果。下面用**时序图**看整个过程，
**每一个箭头旁边都标着该阶段的提示词（prompt）内容**：

```mermaid
sequenceDiagram
    autonumber
    participant A as 调用方<br/>pipeline.run()
    participant B as 打包器<br/>build_function_calling_payload
    participant M as 大模型<br/>(无状态)
    participant V as 校验层<br/>validate / _check

    A->>B: 输入文本（原始 prompt）
    B->>M: POST 请求①<hr/>messages = 原始文本<br/>tools = [SCHEMA] + tool_choice
    Note over M: 模型「读到」SCHEMA<br/>(经 tools 转工具令牌)
    M-->>A: 返回①<hr/>tool_calls.arguments<br/>(JSON 字符串)
    A->>V: validate(SCHEMA)<hr/>语法层 json.loads<br/>+ Schema 层
    V-->>A: ❌ 校验失败<br/>e.g. root.age 应为 integer 实为 str
    A->>B: 重试 prompt<hr/>原始文本 + 错误批注
    B->>M: POST 请求②<hr/>messages = 原文 + 批注<br/>tools = [SCHEMA] 照发
    M-->>A: 返回②<hr/>修正后的 JSON
    A->>V: validate(SCHEMA) 再校验
    V-->>A: ✅ 通过 → 拿到结果
    Note over A: 若重试耗尽仍失败 → 兜底 None
```

**每个阶段的完整 prompt 内容（对应时序图中的请求①/请求②）：**

| 阶段                 | 发给模型的 prompt（messages 内容）                                                                                                 | SCHEMA 发给模型？ |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------- | ------------ |
| 请求①（时序图第 2~3 行）    | `患者张三，32岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13800000000。`                                                                         | ✅ 在 tools 通道 |
| 请求②（时序图第 7~8 行，重试） | `患者张三，32岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13800000000。`<br/>【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】<br/>`root.age: 类型应为 integer，实际 str` | ✅ 照发         |

**SCHEMA 的两个角色（同一份，两端各用一次）：**

| 时机           | SCHEMA 干什么                                 | 会不会给大模型                      |
| ------------ | ------------------------------------------ | ---------------------------- |
| ② 打包请求体（6.2） | 被塞进 `tools[].function.parameters`，作为"表"的约束 | ✅ **会**                      |
| ③ 发送请求（6.4）  | 随请求体一起发出去                                  | ✅ **就在这一步给**（经 tools → 工具令牌） |
| ④ 校验返回（6.5）  | 被 `_check(SCHEMA)` 当裁判，检查模型返回的 JSON        | ❌ 不再发（此时在本地当校验规则）            |
| 🔁 重试（6.6）   | 错误批注追加到 prompt，SCHEMA **照发**               | ✅ 重试的每次请求都再发一遍               |

> **关键认知**：大模型是无状态的，每次请求都要重新带上 `tools`（含 SCHEMA）。所以"发多少次请求，
> SCHEMA 就跟着进多少次"。模型侧只负责"尽量填对"，**符不符合表**由本地用同一份 SCHEMA 把关。

### 6.2 打包请求体：`tools` / `tool_choice` 怎么拼进去的（核心！）

这是全文最直白的证据——**`tools` 和 `tool_choice` 就是在这里被并排拼进请求体的**：

```python
# [AGC:START] tool=Cc author=fangkun
def _base_payload(text: str) -> dict:
    p = {"model": MODEL, "messages": [{"role": "user", "content": text}], "temperature": TEMPERATURE}
    if MAX_TOKENS:
        p["max_tokens"] = MAX_TOKENS
    if QWEN_THINKING_OFF:
        p["enable_thinking"] = False
    return p

def build_function_calling_payload(text: str) -> dict:
    """主通道：schema 装进 tools[].function.parameters，提示词零改动。"""
    p = _base_payload(text)
    p["tools"] = [{"type": "function", "function": {
        "name": SCHEMA["name"], "description": SCHEMA["description"], "parameters": SCHEMA}}]
    p["tool_choice"] = {"type": "function", "function": {"name": SCHEMA["name"]}}
    return p

def build_json_mode_payload(text: str) -> dict:
    """对照通道：不发 tools，schema 必须写进 prompt（且含 "JSON" 字样）。"""
    p = _base_payload(text)
    p["messages"] = [
        {"role": "system", "content": "你只输出合法 JSON，且必须符合以下 JSON Schema：\n"
                                      + json.dumps(SCHEMA, ensure_ascii=False)},
        {"role": "user", "content": text},
    ]
    p["response_format"] = {"type": "json_object"}
    return p
# [AGC:END]
```

**两个函数对比，一眼看懂两条通道的差异本质：**

| 打包方式 | messages 提示词 | tools | tool_choice | response_format | 模型侧行为 |
|---|---|---|---|---|---|
| `function_calling` | 零改动 | ✓ 装 schema | ✓ 强制 | 无 | 必须工具调用，JSON 在 `tool_calls[0].args` |
| `json_mode` | **必须自己把 schema 写进 system** | ✗ | ✗ | `{"type":"json_object"}` | 只保证合法 JSON，JSON 在 `content` |

> **json_mode 是唯一需要你在提示词里动手的通道**：它不发 `tools`，模型不知道 `PatientRecord`
> 长什么样，所以你必须手动把 schema 文本拼进 system 消息。而 function_calling 通道，你的提示词
> 一个字都不用动。

### 6.3 完整 prompt 长什么样：两种通道对照（理解的关键）

前面讲了打包逻辑，现在把**完整的 prompt** 摊开，亲眼看两种通道对"你说的话"动了什么手脚。
以下面这句输入为例：

```
患者张三，32岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13800000000。
```

**function_calling 通道：完整请求体 —— messages 一字未动**

```json
{
  "model": "qwen3.6-plus",
  "messages": [
    {"role": "user", "content": "患者张三，32岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13800000000。"}
  ],
  "temperature": 0,
  "enable_thinking": false,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "PatientRecord",
        "description": "自由文本 -> 结构化病历抽取的演示 Schema。",
        "parameters": {
          "type": "object",
          "additionalProperties": false,
          "required": ["name", "age", "symptoms", "risk_level"],
          "properties": {
            "name":       {"type": "string"},
            "age":        {"type": "integer"},
            "symptoms":   {"type": "array", "items": {"type": "string"}},
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "contact": {
              "type": ["object", "null"],
              "additionalProperties": false,
              "properties": {"email": {"type": ["string", "null"]},
                             "phone": {"type": ["string", "null"]}}
            }
          }
        }
      }
    }
  ],
  "tool_choice": {"type": "function", "function": {"name": "PatientRecord"}}
}
```

**盯住 `messages`**：它只有一条 `user`，`content` 就是你说的原文——**一个字都没改**。
表格 schema 全在平行的 `tools` 通道里，模型是通过「工具令牌」读到它的，这就是"提示词零改动"的完整证据。

**json_mode 通道：完整请求体 —— prompt 被改写了**

```json
{
  "model": "qwen3.6-plus",
  "messages": [
    {
      "role": "system",
      "content": "你只输出合法 JSON，且必须符合以下 JSON Schema：\n{\"name\": \"PatientRecord\", \"description\": \"自由文本 -> 结构化病历抽取的演示 Schema。\", \"type\": \"object\", \"additionalProperties\": false, \"required\": [\"name\", \"age\", \"symptoms\", \"risk_level\"], \"properties\": {\"name\": {\"type\": \"string\"}, \"age\": {\"type\": \"integer\"}, \"symptoms\": {\"type\": \"array\", \"items\": {\"type\": \"string\"}}, \"risk_level\": {\"type\": \"string\", \"enum\": [\"low\", \"medium\", \"high\"]}, \"contact\": {\"type\": [\"object\", \"null\"], \"additionalProperties\": false, \"properties\": {\"email\": {\"type\": [\"string\", \"null\"]}, \"phone\": {\"type\": [\"string\", \"null\"]}}}}}"
    },
    {"role": "user", "content": "患者张三，32岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13800000000。"}
  ],
  "temperature": 0,
  "enable_thinking": false,
  "response_format": {"type": "json_object"}
}
```

**对比 `messages`**：多了 `system` 一条，它的 `content` 正是代码里那句
`"你只输出合法 JSON，且必须符合以下 JSON Schema：\n" + json.dumps(SCHEMA, ensure_ascii=False)`——
**整张表格被序列化成一长串文本，硬塞进了提示词**。因为 json_mode 不发 `tools`，模型上下文里
没有工具令牌，只能靠你把 schema 写进它"听到的话"里。

> 一句话对照：
> - function_calling：**prompt 零改动**，表格走 `tools` 通道平行送达。
> - json_mode：**prompt 被改写**，表格被序列化后写进 `system` 消息。

**重试时的完整 prompt（修复层）**

无论哪种通道，重试时 prompt 都会**在原文后面追加错误批注**（`FIX_TEMPLATE`）：

```
患者张三，32岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13800000000。

【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】
root.age: 类型应为 integer，实际 str
```

模型看到的是**上一次具体的校验错误**，于是针对性修正——这就是 §4.4 讲的"重试 = 模型自纠正"。

#### 完整 prompt（模型视角）：SCHEMA 确实在模型输入里

"prompt"这个词有两个视角，理解它们，上面的困惑就没了：

| 视角 | 指什么 | SCHEMA 在吗？ |
|---|---|---|
| **请求体视角**（你发的） | `messages` 里的聊天文本 | ❌ 不在（SCHEMA 在平行的 `tools` 里） |
| **模型视角**（模型读的） | 模型的整个输入上下文 | ✅ **在**（工具令牌形式） |

function_calling 下，模型的完整输入上下文 = **聊天文本（提示令牌）+ 工具定义（工具令牌，SCHEMA 在这里）**：

```mermaid
flowchart TB
    subgraph 模型输入["🧠 模型完整输入上下文"]
        A["① 提示令牌<br/>用户：患者张三，32岁，因发热咳嗽就诊……"]
        B["② 工具令牌 ← SCHEMA 在这里<br/>函数名 PatientRecord<br/>必填 [name,age,symptoms,risk_level]<br/>字段类型 / 枚举 low,medium,high"]
        C["③ 约束<br/>必须调用 PatientRecord（tool_choice）"]
    end
    style A fill:#e3f2fd,stroke:#1565c0
    style B fill:#e8f5e9,stroke:#388e3c
    style C fill:#fff3e0,stroke:#f57c00
```

工具令牌具体展开（示意，推理服务内部把 `tools` 转成类似这样的定义喂给模型，各服务令牌格式略有差异）：

```
<工具: PatientRecord>
  描述: 自由文本 -> 结构化病历抽取的演示 Schema。
  参数:
    name:        字符串（必填）
    age:         整数（必填）
    symptoms:    字符串数组（必填）
    risk_level:  字符串，枚举：low / medium / high（必填）
    contact:     对象或 null：
                  email: 字符串或 null
                  phone: 字符串或 null
  额外字段: 禁止（additionalProperties: false）
</工具>

[约束] 你必须发起一次对 PatientRecord 的工具调用。
```

**结论（把两个视角钉在一起）：**

- 你**发**的 prompt（`messages`）**不含** SCHEMA——提示词零改动。
- 但模型**读到的完整输入含 SCHEMA**——经 `tools` 工具令牌送进去。
- 所以"SCHEMA 不在 prompt 里"与"完整 prompt 包含 SCHEMA"都对，只是"prompt"分别指**你发的文本**和**模型读的输入**。

### 6.4 发请求 + 取 JSON：urllib 直连

```python
# [AGC:START] tool=Cc author=fangkun
import urllib.request

def chat_completion(payload: dict) -> dict:
    """POST {BASE_URL}/chat/completions，返回 OpenAI 兼容的完整响应体。"""
    url = BASE_URL.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

def extract(payload: dict) -> RawResult:
    """发送请求，从响应里取 JSON：function_calling 在 tool_calls[0].args，json_mode 在 content。"""
    data = chat_completion(payload)
    msg = data["choices"][0]["message"]
    tc = msg.get("tool_calls")
    if tc:
        return RawResult(tc[0]["function"]["arguments"])
    content = msg.get("content") or ""
    if content.strip():
        body = _strip_json(content)
        if body:
            return RawResult(body)
        return RawResult(None, "content 中未找到 JSON 对象")
    return RawResult(None, "模型未返回工具调用或文本内容")
# [AGC:END]
```

**对照 §3.6**：`tc[0]["function"]["arguments"]` 正是函数调用协议规定的那段 JSON 字符串；
没有 tool_calls 就退到 `content` 抠 JSON——和大块一、二完全同一套逻辑。

### 6.5 校验层：手写 `_check()` 等价于 Pydantic 校验

没有 Pydantic，就用递归手写校验：必填字段、类型、枚举、禁多余字段。**注意 `type(value) is int`
这个写法——它用 `is` 排除 bool，因为 Python 里 `bool` 是 `int` 的子类。**

```python
# [AGC:START] tool=Cc author=fangkun
def _match_type(value, t: str) -> bool:
    if t == "string":  return isinstance(value, str)
    if t == "integer": return type(value) is int                      # type is 排除 bool
    if t == "number":  return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean": return isinstance(value, bool)
    if t == "object":  return isinstance(value, dict)
    if t == "array":   return isinstance(value, list)
    if t == "null":    return value is None
    return True

def _check(data, schema: dict, path: str = "root") -> list[str]:
    """递归校验 data 是否符合 schema，返回错误列表（空列表 = 通过）。"""
    errors: list[str] = []
    types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    if not any(_match_type(data, t) for t in types):
        errors.append(f"{path}: 类型应为 {schema['type']}，实际 {type(data).__name__}")
        return errors
    if "object" in types and isinstance(data, dict):
        props = schema.get("properties", {})
        for key in data:                                # additionalProperties: false
            if key not in props:
                errors.append(f"{path}.{key}: 不属于 schema 的字段")
        for key in schema.get("required", []):          # 必填字段
            if key not in data:
                errors.append(f"{path}.{key}: 缺少必填字段")
        for key, sub in props.items():                  # 递归子字段
            if key in data:
                errors += _check(data[key], sub, f"{path}.{key}")
    if "array" in types and isinstance(data, list):
        for i, item in enumerate(data):
            errors += _check(item, schema.get("items", {}), f"{path}[{i}]")
    if "enum" in schema and data not in schema["enum"]:  # 枚举合法性
        errors.append(f"{path}: 枚举值 {data!r} 不在 {schema['enum']}")
    return errors

def validate(raw: RawResult) -> dict:
    """语法层 + Schema 层；任何一层失败都抛 ValueError，交给 ④ 重试。"""
    if not raw.json_str:
        raise ValueError(raw.note or "模型未返回可解析的 JSON")
    data = json.loads(raw.json_str)                     # 语法层
    errs = _check(data, SCHEMA)                         # Schema 层
    if errs:
        raise ValueError("；".join(errs))
    return data
# [AGC:END]
```

> **对照大块一**：这里的 `_check()` 递归，等价于 `pipeline.py` 里 `schema.model_validate(data)`
> 在这套 schema 上做的全部检查。两层校验语义完全相同：
> **模型输出的 JSON 必须严格等于你的契约，差一点就判失败并进入重试。**

### 6.6 修复层 + 兜底层 + 观测：闭环与前面完全同构

```python
# [AGC:START] tool=Cc author=fangkun
FIX_TEMPLATE = "\n\n【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】\n{error}"
LOG_FILE = "logs/pure_structured_output.jsonl"

def run(text: str, builder, *, fallback: dict | None = None):
    """返回 (解析结果 | fallback, 实际尝试次数, 错误列表, 日志记录列表)。"""
    errors: list[str] = []
    records: list[dict] = []                            # 日志先攒在这，流程跑完再统一写出
    last_prompt, last_raw = text, RawResult(None, "")
    started = time.perf_counter()
    for attempt in range(1, MAX_RETRIES + 2):
        last_prompt = text if attempt == 1 else text + FIX_TEMPLATE.format(error=errors[-1])
        last_raw = extract(builder(last_prompt))
        try:
            obj = validate(last_raw)
        except (json.JSONDecodeError, ValueError) as exc:   # 语法层 / Schema 层失败
            errors.append(f"{type(exc).__name__}: {exc}")
            records.append(_record(attempt, "retry", last_prompt, last_raw, None, errors[-1], started))
            continue
        records.append(_record(attempt, "ok", last_prompt, last_raw, obj, "", started))
        write_records(records)                          # 流程结束，统一落盘
        return obj, attempt, errors, records
    last = errors[-1] if errors else "重试耗尽"
    records.append(_record(MAX_RETRIES + 1, "fallback", last_prompt, last_raw, None, last, started))
    write_records(records)                              # 流程结束，统一落盘
    return fallback, MAX_RETRIES + 1, errors, records
# [AGC:END]
```

### 6.7 运行命令

```bash
# 真实调用
cd python && python -m src.structured_output.pure_structured_output

# 只看请求体（不发请求，最适合学习）→ 把 §三 那张三块并列的图打出来给你看
python -m src.structured_output.pure_structured_output --dry-run

# 切换 json_mode 对比两条通道
python -m src.structured_output.pure_structured_output --method json_mode
```

> **`--dry-run` 是这一版的精华**：它把 `build_function_calling_payload` 的结果直接
> `json.dumps(..., indent=2)` 打印出来——你在屏幕上看到的，就是 §6.3 那张完整请求体 JSON 本身。

---

### 6.8 扩展：多种 schema，怎么保证返回的是其中一种？

**场景**：不只是病历（`PatientRecord`），还有化验单（`LabReport`）、处方（`Prescription`）……
模型要根据输入判断该返回哪种格式，而且必须**严格符合其中某一种**，不能东拼西凑。

**核心思路：一个 schema = 一个工具。** 单 schema 时 `tools` 数组里只有一个函数；
多 schema 就是把 `tools` 数组里放多个函数，让模型**自己选**。

```mermaid
---
title: "多 schema = 多工具，模型自选"
---
flowchart TD
    T["🧰 tools 数组<br/>PatientRecord + LabReport + Prescription"] --> M["🧠 模型根据输入自选"]
    M --> R["tool_calls[0].function.name<br/>= 它选中的格式"]
    R --> V["✅ 用 name 对应的 schema 校验<br/>(不是固定单一 schema)"]
    V -- "❌ 失败" --> RETRY["🔁 重试：<br/>你选了 X 但不符合 X 的 schema"]
    RETRY --> M

    style T fill:#e3f2fd,stroke:#1565c0
    style M fill:#fff3e0,stroke:#f57c00
    style V fill:#e8f5e9,stroke:#388e3c
    style RETRY fill:#ffcdd2,stroke:#c62828
```

**关键机制（与单 schema 的 4 个差异）：**

| 环节 | 单 schema | 多 schema |
|---|---|---|
| `tools` 数组 | 1 个函数 | 多个函数 |
| `tool_choice` | 强制指定该工具 | **不写 / auto**——模型必须选、但不限定选哪个 |
| 模型返回 | `arguments` | `arguments` + `function.name`（**name 就是它选的格式**） |
| 校验层 | 固定用一个 schema | **按 name 找对应 schema** 校验 |

**① 改打包：tools 数组放多个函数（纯 Python 视角）**

```python
# [AGC:START] tool=Cc author=fangkun
SCHEMAS = [PATIENT_SCHEMA, LAB_SCHEMA, PRESCRIPTION_SCHEMA]   # 多个 schema

def build_multi_tool_payload(text: str) -> dict:
    p = _base_payload(text)
    p["tools"] = [{"type": "function", "function": {
        "name": s["name"], "description": s["description"], "parameters": s}} for s in SCHEMAS]
    # ⚠️ 不写 tool_choice：单 schema 是"强制点某一道菜"，多 schema 是"从菜单里选一道，但必须选一道"
    return p
# [AGC:END]
```

**② 取返回：name 和 JSON 一起拿**

```python
# [AGC:START] tool=Cc author=fangkun
def extract_multi(payload: dict) -> tuple[str | None, RawResult]:
    """返回 (模型选中的工具名, JSON)。name=None 表示没走工具调用。"""
    data = chat_completion(payload)
    msg = data["choices"][0]["message"]
    tc = msg.get("tool_calls")
    if tc:
        # name 告诉我们是哪种格式，arguments 是该格式的 JSON
        return tc[0]["function"]["name"], RawResult(tc[0]["function"]["arguments"])
    return None, RawResult(None, "content 中未找到 JSON 对象")
# [AGC:END]
```

**③ 改校验：按 name 分派 schema**

```python
# [AGC:START] tool=Cc author=fangkun
def validate_multi(raw: RawResult, name: str) -> dict:
    if not raw.json_str:
        raise ValueError(raw.note or "模型未返回可解析的 JSON")
    schema = {s["name"]: s for s in SCHEMAS}[name]   # ⚠️ 按 name 选对应 schema
    data = json.loads(raw.json_str)
    errs = _check(data, schema)                       # 用选中的 schema 校验
    if errs:
        raise ValueError("；".join(errs))
    return data
# [AGC:END]
```

**两种"多格式"姿势对比：**

| 姿势 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| **多工具自选**（推荐） | tools 数组放多个函数，模型自选，返回 name | 模型原生会区分；校验精确到某一种 | 模型可能"选错类"或输出混合字段 → 靠重试救 |
| **Union 单工具** | 一个 schema 用 `Union[A, B, C]`（anyOf） | 语义上是"一种多分支" | deepseek/qwen 对 anyOf 支持不完美；模型可能各取一部分拼凑 |

**对闭环的影响**：重试的 prompt 要更具体——**"你调用了 X 工具，但输出不符合 X 的 schema：错误详情"**，
让模型针对性修正它选的那一类，而不是笼统地说"输出不对"。

---

### 6.9 扩展：模型"选错类"（标签选错 / 字段混杂）怎么兜底？

**多工具 = 开放式选择，模型就可能选错。** 典型场景：

| 翻车方式 | 现象 |
|---|---|
| **标签选错** | 内容明明是一份病历，模型却选中了 `LabReport` 工具 |
| **字段混杂** | 输出既像病历又有化验单字段，两类各取一部分拼凑 |

好在 schema 校验天然能发现：每个 schema 都带 `additionalProperties:false` + 自己的
`required` 字段列表，**"选错类"几乎必然校验失败**——内容与所选 schema 对不上。

**兜底分三道，优先级从高到低：**

```mermaid
---
title: "选错类的三道兜底"
---
flowchart TD
    M["🧠 模型返回<br/>name + JSON"] --> V1["① 按自选的 name 校验"]
    V1 -->|"✅ 通过"| OK["✅ 收下"]
    V1 -->|"❌ 失败"| V2["② 逐个 schema 试一遍<br/>内容对、只是标签错?"]
    V2 -->|"✅ 有 schema 通过"| OK
    V2 -->|"❌ 全都不符"| RETRY["③ 抛错进重试<br/>错误信息带上它选的 name"]
    RETRY -->|"重试耗尽"| FB["🛟 兜底 fallback"]

    style OK fill:#e8f5e9,stroke:#388e3c
    style V1 fill:#e3f2fd,stroke:#1565c0
    style V2 fill:#fff3e0,stroke:#f57c00
    style RETRY fill:#ffcdd2,stroke:#c62828
    style FB fill:#fce4ec,stroke:#c2185b
```

**为什么第 ② 道这么设计？** 现实中"模型选错标签但内容其实是完整的某一种"很常见。
如果按 name 校验失败就直接丢给模型重试，等于**白白多花一次请求**；
先逐个 schema 试一遍，能命中就当场放行，省一次交互。

**增强版校验（纯 Python 视角，替换 §6.8 的 `validate_multi`）：**

```python
# [AGC:START] tool=Cc author=fangkun
SCHEMAS_BY_NAME = {s["name"]: s for s in SCHEMAS}

def validate_multi(raw: RawResult, name: str | None) -> dict:
    """① 按自选 name 校验 → ② 选错标签则逐个 schema 兜底 → ③ 全不符抛错。"""
    if not raw.json_str:
        raise ValueError(raw.note or "模型未返回可解析的 JSON")
    data = json.loads(raw.json_str)
    primary = SCHEMAS_BY_NAME.get(name)          # 模型自选的那个
    if primary and not _check(data, primary):    # ① 先按它选的校验
        return data
    for s in SCHEMAS:                            # ② 选错标签兜底：内容对就放行
        if not _check(data, s):
            return data
    # ③ 全都不符 → 抛错，交给重试（错误信息带上它选的 name）
    raise ValueError(
        f"你选择了 {name}，但输出不符合它，也不符合其它任何 schema；"
        f"请只输出其中一种的完整字段")
# [AGC:END]
```

**与"一失败就重试"的对比：**

| 策略 | 标签选错 + 内容对 | 内容真的混杂 |
|---|---|---|
| **一失败就重试** | 浪费 1 次请求 | 重试，模型可能再次拼凑 |
| **先逐个试（本方案）** | 当场放行，0 次浪费 | 仍走重试，但错误信息更具体 |

> ⚠️ **边界**：第 ② 道的"逐个试"本质是**让校验层做一次模糊匹配**，代价是稍慢（N 个 schema 就跑 N 次 `_check`）。
> schema 数量多、对准确性要求苛刻时，可以关掉第 ② 道，让"选错"一律进重试——重试耗尽再用第 ③ 道之外的 fallback 兜底。

---

### 6.10 扩展：LangChain 多 schema 的等价写法

**`with_structured_output()` 绑定的是单一 schema，不接受工具数组。** 多 schema 要走 LangChain
的**工具绑定**路：**`bind_tools([Pydantic 类...])`**——每个 Pydantic 类自动变成一个工具
（类名 → 工具名，docstring → description，字段 → JSON Schema），等价于 §6.8 手拼的 tools 数组。

```python
# [AGC:START] tool=Cc author=fangkun
llm = build_llm()                                  # 裸 ChatOpenAI，不加 with_structured_output

# 一个 Pydantic 类 = 一个工具 = 一个 schema；三个类 = tools 数组三个函数
bound = llm.bind_tools([PatientRecord, LabReport, Prescription])
# ⚠️ 不设 tool_choice = auto：模型从菜单里选一道，但必须选一道（正是 §6.8 的要求）

res = bound.invoke(text)                           # 返回 AIMessage，不是 dict
tc = res.tool_calls[0]                             # {'name': 'LabReport', 'args': {...}}
name, args = tc["name"], tc["args"]                # name = 模型自选的格式

raw = RawResult(json.dumps(args, ensure_ascii=False))
data = validate_multi(raw, name)                   # 复用 §6.9 的校验（含选错类兜底）
# [AGC:END]
```

**注意一个差别**：`with_structured_output` 把 JSON 藏在 `res.get("raw").tool_calls[0].args` 里
（要 `include_raw=True` 才拿得到）；而 `bind_tools` 直接挂在 `res.tool_calls[0]` 上，
没有 include_raw 那层壳。**两条路最终都是同一个函数调用协议。**

**两种写法对比：**

| 维度 | `with_structured_output(Schema)` | `bind_tools([类1, 类2, 类3])` |
|---|---|---|
| 支持 schema 数量 | 单一 | 多个 |
| 工具如何生成 | 内部绑定一个函数 | 每类一个函数 |
| tool_choice | 内部强制指定 | 不设 = auto，模型自选 |
| JSON 在哪 | `res["raw"].tool_calls[0].args` | `res.tool_calls[0].args` |
| 模型选了什么 | 不用关心（只有一个） | 看 `res.tool_calls[0]["name"]` |
| 校验 | 固定一个 schema | 复用 §6.9 `validate_multi` |

**一句话**：单 schema 用 `with_structured_output`（省心）；多 schema 用 `bind_tools`（模型自选 + 拿 name）——
底层都是"tools 数组 + 函数调用协议"，校验闭环一条代码都不浪费。

---

## 七、三版本对比总览

```mermaid
---
title: "三套代码 = 同一原理的三种写法"
---
flowchart TB
    ROOT["⚙️ 同一套原理<br/>请求体三块并列 + 函数调用协议 + 校验重试兜底"]
    ROOT --> V1["📁 多文件 LangChain 版<br/>分层清晰，生产用法"]
    ROOT --> V2["📄 单文件 LangChain 版<br/>平铺注释细，教学对照"]
    ROOT --> V3["🔧 原生 Python 版<br/>手拼请求体，看本质"]

    style ROOT fill:#e3f2fd,stroke:#1565c0,stroke-width:3px
    style V1 fill:#e8f5e9,stroke:#388e3c
    style V2 fill:#fff3e0,stroke:#f57c00
    style V3 fill:#f3e5f5,stroke:#7b1fa2
```

| 维度 | 多文件 LangChain 版 | 单文件 LangChain 版 | 原生 Python 版 |
|---|---|---|---|
| 文件 | `pipeline`/`extractors`/`schemas`/`observability`/`config`/`demo` | `simple_onefile.py` | `pure_structured_output.py` |
| 依赖 | LangChain | LangChain | 纯标准库 urllib |
| 请求体怎么来的 | `with_structured_output()` 帮你拼 | 同上 | 手拼（看得见） |
| 校验 | Pydantic `model_validate` | Pydantic `model_validate` | 手写 `_check()` 递归 |
| 适合 | 生产 / 上线 | 教学 / 读懂分层 | 学原理 / 排障 |
| 重点看清 | 每一层负责什么 | 层与层如何调用 | `tools`/`tool_choice` 怎么拼进请求体 |

**学习路线建议**：多文件版跑通 → 单文件版逐段读懂 → 原生版 `--dry-run` 把请求体摊开亲眼看一遍。

---

## 八、三条通道全景 + 版本坑

### 8.1 全景对照表

| 策略 | 机制 | 保证强度 | 适用模型 | 备注 |
|---|---|---|---|---|
| `with_structured_output(method="function_calling")` | 把 schema 伪装成工具，`tool_choice` 强制调用 | 语法层强 | 支持 tool calling 的模型（deepseek/qwen ✓） | **现代主路径** |
| `with_structured_output(method="json_mode")` | 传 `response_format={"type":"json_object"}` | 语法层中 | 支持 json mode 的模型 | **现代主路径** |
| `with_structured_output(method="json_schema")` | 传 `response_format={"type":"json_schema"}` | 语法层最强（严格 schema） | 仅 OpenAI/Claude/Gemini | deepseek/qwen **不可用** |

### 8.2 版本坑：不传 method 会 400

> ⚠️ **langchain-openai 1.4+ 的 `with_structured_output` 不传 `method` 时，默认已是 `json_schema`**
> （不再是 0.x 的 `function_calling`）。而 `json_schema` 严格模式仅 OpenAI/Claude/Gemini 支持；
> deepseek/qwen 收到 `response_format.type=json_schema` 直接 400。
>
> **deepseek/qwen 必须显式传 `method="function_calling"`（最稳）或 `"json_mode"`。**
> 三套代码里的 `method="function_calling"` 就是这么来的。

### 8.3 两个通用坑

| 坑 | 现象 | 解法 |
|----|------|------|
| prompt 缺 "JSON" 字样 | deepseek 输出空白流；qwen 直接 API 报错 | json_mode 内部指令通常已含；手写 prompt 自查 |
| 设置了过低的 `max_tokens` | 输出被截断 → 坏 JSON | 结构化输出默认不设 max_tokens；确要设则给高值 |

---

## 九、可视化总览：五层保证闭环

```mermaid
flowchart TB
    subgraph 模型侧["🧠 模型侧（尽力而为）"]
        M1["语法层<br/>function_calling / json_object<br/>尽量输出合法 JSON"]
    end
    subgraph 客户端["💻 客户端（硬保证）"]
        C1["Schema 层<br/>Pydantic 严格校验"]
        C2["修复层<br/>错误喂回重试"]
        C3["兜底层<br/>重试耗尽返回 fallback"]
        C4["观测层<br/>JSONL 日志 + 失败计数"]
    end
    M1 --> C1 --> C2 --> C3 --> C4
    style 模型侧 fill:#e3f2fd,stroke:#1565c0
    style 客户端 fill:#e8f5e9,stroke:#388e3c
```

---

## 十、关键数字速记

```
┌────────────────────────────────────────────────────────┐
│  📊 关键数字（记这几个就够）                            │
├────────────────────────────────────────────────────────┤
│  • 3 块平级字段：messages / tools / tool_choice         │
│  • 3 套代码：多文件 → 单文件 → 原生 Python              │
│  • 3 条通道：function_calling / json_mode / json_schema │
│  • 2 层校验：语法层 json.loads + Schema 层 model_validate│
│  • 2 次默认重试：max_retries=2（共 3 次尝试）            │
│  • 1 个兜底：默认 None（宁缺毋滥）                      │
│  • 1 个死命令：tool_choice 锁死必须调用指定工具          │
└────────────────────────────────────────────────────────┘
```

---

## 十一、类比速记卡

| 概念 | 类比 | 一句话 |
|---|---|---|
| 结构化输出 | 去诊所填病历表 | 让大模型把话填进固定格子 |
| messages（提示词） | 你说的话 | 提供信息，function_calling 下零改动 |
| tools | 空表清单/菜单 | 告诉大模型"有这张表要填" |
| tool_choice | 死命令/点菜 | 锁死大模型必须填这张表 |
| tool_calls[].arguments | 前台交回的填好的表 | 里面是一整个 JSON 字符串 |
| content | 模型直接吐的文本 | json_mode 通道下 JSON 在这里 |
| 校验 | 检查表填没填对 | 缺填/类型错/不在选项/多填栏都算失败 |
| 重试 | 退回去重填 | 把错误批注喂回去，模型针对性修正 |
| 兜底 | 宁缺毋滥 | 改不好就返回空，不拿错的硬用 |

---

## 十二、生产级落地：从"能跑"到"放心跑"

前八章讲完了**原理**（请求体三块并列）和**三套能跑的闭环**。但"能跑"和"生产放心"是两回事——
§6.8~6.10 让模型"自选格式"，生产上你会遇到四个真实问题：

| 生产问题 | 现象 | 靠什么解决 |
|---|---|---|
| **路由错误** | 模型把病历选成化验单 | 架构上把"选类"独立出来 |
| **重试不收敛** | 模型在两类之间反复横跳 | 错误反馈更具体 + 人工兜底 |
| **模糊放行** | §6.9 的"逐个试"放过半对 | 语义校验加一道 |
| **fallback=None** | 上游要么崩要么静默 | 有业务意义的降级 |

**核心答案一句话：生产可靠性不是靠"更多校验、更多重试"堆出来的，而是靠架构上"减少模型做高风险决策的机会，把不可靠性隔离到最小的环节里"。**

> 配套代码：[python/src/structured_output/prod_singlefile.py](https://github.com/kunge2013/LangChainBestPractices/blob/main/python/src/structured_output/prod_singlefile.py)

### 12.1 一次架构转身：让模型做"选择题"，而不是"填空题+自选"

§6.8 让模型**同时回答两个问题**："这是哪类？" + "按这类输出完整 JSON"。两个都难，还互相干扰。

生产级的转身：**路由与生成分离**。先把"这是哪类"拆成一个单独的小步骤（Router），再对选中的**单一 schema**做结构化输出（Extractor）。每一步单一职责、出错率可单独观测、可单独降级。

```mermaid
---
title: "生产流水线：Router → Extractor → 两层校验 → 人工兜底"
---
flowchart LR
    IN["📥 输入<br/>病历/化验单/处方…"] --> R1["① 规则路由<br/>关键词/正则<br/>零成本 100% 可解释"]
    R1 -->|"命中"| R2
    R1 -->|"判不出"| R2["② 模型路由<br/>做选择题:<br/>这属于哪类?<br/>枚举+置信度"]
    R2 -->|"置信度低"| HUM["👤 人工队列"]
    R2 -->|"选中 A 类"| EX["③ 抽取<br/>单一 schema<br/>with_structured_output"]
    EX --> V1["④a schema 校验<br/>Pydantic 格式层"]
    V1 --> V2["④b 语义校验<br/>业务规则层"]
    V2 -->|"✅ 两层都过"| OK["✅ 入库"]
    V2 -->|"❌"| RETRY["🔁 重试 N 次<br/>错误反馈带具体字段"]
    RETRY -->|"仍失败"| HUM
    RETRY --> EX

    style R1 fill:#e8f5e9,stroke:#388e3c
    style R2 fill:#fff3e0,stroke:#f57c00
    style EX fill:#e3f2fd,stroke:#1565c0
    style V1 fill:#f3e5f5,stroke:#7b1fa2
    style V2 fill:#fce4ec,stroke:#c2185b
    style HUM fill:#ffcdd2,stroke:#c62828
    style OK fill:#c8e6c9,stroke:#2e7d32
```

### 12.2 环节① 规则路由：能规则，就不模型

**原则：能规则就不模型，能选择题就不填空题。** 病历/化验单/处方差异明显，关键词就能判：

```python
# [AGC:START] tool=Cc author=fangkun
class RuleRouter:
    """确定性关键词映射：零成本、零随机、100% 可解释。"""
    RULES = [
        ("lab_report",     ["血常规", "白细胞", "体温", "化验"]),
        ("prescription",   ["剂量", "用法", "一日", "毫克", "处方"]),
        ("patient_record", ["症状", "咳嗽", "发烧", "门诊"]),
    ]

    def route(self, text: str) -> RouteResult | None:
        hits = [name for name, kws in self.RULES if any(k in text for k in kws)]
        if len(hits) == 1:                       # 唯一命中才敢下判断
            return RouteResult(DocKind(hits[0]), 1.0, "rule", f"关键词命中:{hits[0]}")
        if len(hits) > 1:
            return None                          # 多个命中=模棱两可，交给模型
        return None                              # 一个都没命中，交给模型
# [AGC:END]
```

> 规则只负责"能确定的部分"，**模棱两可必须上交**给模型——规则乱猜比模型猜更可怕（没有置信度概念）。

### 12.3 环节② 模型路由：做"选择题"不是"填空题"

规则判不出时，让模型输出一个**枚举 + 置信度**，而不是一整份 JSON。选择题的 schema 极小、决策面极小：

```python
# [AGC:START] tool=Cc author=fangkun
class RouteChoice(BaseModel):
    """路由选择题：只要一个答案 + 自评置信度。"""
    model_config = ConfigDict(extra="forbid")
    kind: DocKind                    # 枚举：patient_record / lab_report / prescription
    confidence: int = Field(ge=0, le=100)

class ModelRouter:
    def __init__(self, llm: Any, threshold: float = 0.6) -> None:
        self._runnable = llm.with_structured_output(RouteChoice, method="function_calling", include_raw=True)
        self.threshold = threshold

    def route(self, text: str) -> RouteResult:
        raw = self._runnable.invoke(text).get("raw")
        if raw is None:
            return RouteResult(None, 0.0, "model", "路由调用无输出")
        args = (raw.tool_calls or [{}])[0].get("args", {})
        kind, conf = args.get("kind"), args.get("confidence", 0) / 100
        # 低置信度不等于"随便猜一个":直接标记人工,不在下游赌
        return RouteResult(DocKind(kind) if kind else None, conf, "model", f"置信度{conf:.0%}")
# [AGC:END]
```

**置信度阈值的意义**：`conf < 0.6` → **走人工，不赌**。这是"把不可靠性隔离"的关键一步——
路由错了成本极低（一个小枚举），但会连锁污染后面一整份 JSON 的抽取，所以宁可在入口就分流。

### 12.4 环节③ 抽取：对选中的单一 schema 结构化

路由定案后，**一次只干一件事**：对选中的 schema 做 `with_structured_output`。此时退回最可靠的
单 schema 场景（第四章大块一的 `RealExtractor` 原样复用）：

```python
# [AGC:START] tool=Cc author=fangkun
class SchemaExtractor:
    """单一 schema 的结构化抽取器：每类文档一个实例。"""
    def __init__(self, llm: Any, model_cls: type[BaseModel]) -> None:
        self._runnable = llm.with_structured_output(model_cls, method="function_calling", include_raw=True)
        self.model_cls = model_cls

    def extract(self, text: str) -> RawResult:
        raw = self._runnable.invoke(text).get("raw")
        if raw is None:
            return RawResult(None, "无原始输出", None)
        return pick_json(raw)                    # 复用大块一的 _pick_json
# [AGC:END]
```

### 12.5 环节④ 两层校验：格式层 + 语义层

**Pydantic 校验管"格式"（字段齐不齐、类型对不对），管不了"业务合不合理"（年龄 200 岁、处方没药名）。**
所以生产上是**两层**：

```python
# [AGC:START] tool=Cc author=fangkun
# 第一层:格式层 —— Pydantic model_validate (复用大块一)
def schema_errors(model_cls: type[BaseModel], data: dict) -> list[str]:
    try:
        model_cls.model_validate(data)
        return []
    except ValidationError as exc:
        return [f"{e['loc']}: {e['msg']}" for e in exc.errors()]

# 第二层:语义层 —— 业务规则,每个 kind 自己的规则表
def _patient_semantic(obj) -> list[str]:
    errs = []
    if not (0 < obj.age < 150): errs.append("语义: 年龄必须 1~149")
    if not obj.symptoms:         errs.append("语义: 症状不能为空")
    if obj.contact and not (obj.contact.email or obj.contact.phone):
        errs.append("语义: contact 至少要 email 或 phone 之一")
    return errs

SEMANTIC_RULES = {DocKind.PATIENT: _patient_semantic, ...}   # 每个 kind 一张

def collect_errors(kind: DocKind, model_cls: type[BaseModel], data: dict) -> list[str]:
    return schema_errors(model_cls, data) + SEMANTIC_RULES[kind](model_cls.model_validate(data))
# [AGC:END]
```

> 语义层是**我们自己的代码**，不是模型——它是硬保证的最后一公里：模型可能给你一份"格式合法但
> 业务荒谬"的 JSON，只有语义规则能挡住。

### 12.6 环节⑤ 重试 + 人工兜底 + 观测

重试的**错误反馈必须携带具体字段**（第一层和第二层的错误都拼进去），耗尽后：
- 有业务意义的 fallback（按 kind 的默认实例）**而不是 None**；
- 或标记进**人工队列**（`human_review` 状态），由人兜底。

**观测 = 每个环节都有计数，这是生产与演示的最大区别**：路由来源、置信度分布、校验失败率、
人工介入率各是一个指标，哪个高就修哪个（改关键词？调阈值？换更强模型？）。

```python
# [AGC:START] tool=Cc author=fangkun
class ProdMetrics:
    """按环节分桶计数:谁在拖后腿一目了然。"""
    def __init__(self) -> None:
        self.total = 0; self.ok = 0; self.human = 0; self.fallback = 0
        self.route_source: dict[str, int] = {}
        self.low_confidence = 0; self.validation_failures = 0
    def record_route(self, src: str, conf: float) -> None:
        self.route_source[src] = self.route_source.get(src, 0) + 1
        if conf < 0.6: self.low_confidence += 1
    def summary(self) -> dict:
        return {"total": self.total, "ok": self.ok,
                "human_review": self.human, "fallback": self.fallback,
                "validation_failures": self.validation_failures,
                "route_source": self.route_source,
                "low_confidence": self.low_confidence,
                "success_rate_%": round(self.ok / self.total * 100, 2) if self.total else 0.0}
# [AGC:END]
```

### 12.7 与 §6.8"一把梭"的对比

| 维度 | §6.8 多工具自选（演示够用） | 生产级流水线（单文件版） |
|---|---|---|
| 谁决定类型 | 模型在抽取时顺带选 | **独立 Router 先选**，抽取只管一种 |
| 类型判断形式 | 从多工具里挑（隐性） | **显式枚举选择题 + 置信度** |
| 低置信度 | 无概念，照抽 | **分流走人工，不赌** |
| 校验 | schema 一层 | **schema + 语义两层** |
| 重试反馈 | "你选了 X 但不符合 X" | 具体字段错误（两层都带） |
| 失败出口 | fallback=None | **业务默认值 / 人工队列** |
| 观测 | JSONL 全量 | **按环节分桶指标**，可定位瓶颈 |

### 12.8 最小实现：一个文件 = 一个流水线

整套生产级流水线合并成 **`prod_singlefile.py` 单文件**（不再拆散成多文件），
每个环节用 `═══` 分隔块平铺，从上到下就是调用顺序，与 §12.1 流水线图一一对应：

```
python/src/structured_output/prod_singlefile.py
├── ① 数据模型   三类文档 schema + DocKind 枚举 + 语义规则表
├── ② 路由       RuleRouter(规则) + ModelRouter(选择题) + Router(组合)
├── ③ 抽取       SchemaExtractor(单 schema) + FakeExtractor(离线脚本)
├── ④ 校验       两层 collect_errors()：格式层 + 语义层
├── ⑤ 闭环       ProductionPipeline: 路由→分流→抽取→校验→重试→人工/兜底
├── ⑥ 观测       ProdMetrics 环节计数
└── ⑦ 入口       --fake 离线演示 / 真实调用（--provider qwen|deepseek）
```

运行（`cd python`，配 OPENAI_* 环境变量）：
```
python -m src.structured_output.prod_singlefile --fake   # 离线演示,无需 key
python -m src.structured_output.prod_singlefile          # 真实调用
python -m pytest src/structured_output/tests -q          # 单元测试
```

---

## 十三、一句话总结（费曼技巧版）

**结构化输出是什么？**
> 在发给模型的请求体里，除了你说的话（messages），平行塞进一张空表（tools）和一条死命令
> （tool_choice）；死命令逼模型必须发起一次工具调用，工具调用协议规定 `arguments` 必须是
> 符合表格的 JSON 字符串——于是模型"被迫"返回 JSON。

**为什么重要？**
> 大模型默认像聊天一样自由发挥，电脑没法直接处理。结构化输出把它变成"填表"，让输出可被
> 校验、可被程序直接用；而真正的可靠性来自你自己的"校验 + 重试 + 兜底"闭环。

**一句话记牢：**
> **模型侧尽力而为（协议只保证"是 JSON"），校验层是硬保证（符不符合你的表由你兜底）。**

---

> 📝 **学习笔记**
> - 学习日期：2026-09-09
> - 学习方式：费曼学习法（大白话版）
> - 配套代码：[python/src/structured_output](https://github.com/kunge2013/LangChainBestPractices/tree/main/python/src/structured_output)
> - 学习路线：大块一（多文件版）→ 大块二（单文件版）→ 大块三（原生 Python 版 `--dry-run`）
> - 运行命令：
>   - 多文件版离线演示：`cd python && python -m src.structured_output.demo --fake`
>   - 多文件版真实调用：`python -m src.structured_output.demo --provider qwen --method function_calling`
>   - 单文件版：`python -m src.structured_output.simple_onefile`
>   - 原生版看请求体：`python -m src.structured_output.pure_structured_output --dry-run`
> - 下一步：理解后，用自己的话讲给同事听
