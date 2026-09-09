# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""生产级结构化输出·纯 Python 版：路由与生成分离 + 两层校验 + 人工兜底，无 LangChain。

与 prod_singlefile.py（LangChain 单文件版）逻辑等价，但把模型调用层换成纯标准库：
urllib 直连 OpenAI 兼容接口，手拼请求体（顶层 messages + tools + tool_choice 三块并列），
schema 是纯 dict JSON Schema（不依赖 Pydantic）。机制对应文档 §十二 与 §2.6。

  ① 数据模型  SCHEMA_BY_KIND / ROUTE_SCHEMA（纯 dict JSON Schema）+ DocKind 枚举 + 语义规则
  ② 路由      RuleRouter(规则优先) + ModelRouter(选择题+置信度) + Router(组合)
              规则唯一命中就判；模棱两可上交模型；低置信度不赌，转人工
  ③ 抽取      SchemaExtractor(单 schema) + FakeExtractor(离线剧本)
  ④ 校验      两层：格式层(手写 _check) + 语义业务层(SEMANTIC_RULES)
  ⑤ 闭环      ProductionPipeline：路由→分流→抽取→两层校验→重试→fallback/人工
  ⑥ 观测      ProdMetrics 按环节分桶计数

运行（在仓库 python/ 目录下，配 OPENAI_BASE_URL / OPENAI_MODEL / OPENAI_API_KEY；
      目录名以数字开头，不能 `python -m`，直接跑文件）：
  只看请求体（不发请求）：python src/base_practice/20_prod_structured_output/prod_pure.py --dry-run
  离线演示（无需 key）：python src/base_practice/20_prod_structured_output/prod_pure.py --fake
  真实调用：python src/base_practice/20_prod_structured_output/prod_pure.py
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from dotenv import load_dotenv

load_dotenv(override=True)   # 必须在 env 常量读取之前：BASE_URL/MODEL/API_KEY 依赖它

# [AGC:START] tool=Cc author=fangkun
# ═════════════════════════════════════════════════════════════════
# ① 数据模型：纯 dict JSON Schema（等价 Pydantic 的 model_json_schema()）。
#    class X             -> "name"
#    类 docstring        -> "description"
#    extra="forbid"      -> "additionalProperties": False
#    必填字段            -> "required"
#    str/int/float/list  -> "type"
#    枚举                -> "enum"
#    X | None            -> "type": ["X", "null"]
#    语义规则(SEMANTIC_RULES)管"业务合不合理"，schema 管"格式对不对"。
# ═════════════════════════════════════════════════════════════════
class DocKind(str, Enum):
    """文档类型，同时也是路由的"选择题答案"。"""
    PATIENT = "patient_record"
    LAB = "lab_report"
    PRESCRIPTION = "prescription"


SCHEMA_BY_KIND: dict[DocKind, dict] = {
    DocKind.PATIENT: {
        "name": "PatientRecord",
        "description": "病历：患者信息 + 症状 + 风险评估。",
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
    },
    DocKind.LAB: {
        "name": "LabReport",
        "description": "化验单：患者 + 指标列表 + 结论。",
        "type": "object",
        "additionalProperties": False,
        "required": ["patient_name", "items"],
        "properties": {
            "patient_name": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "value", "unit"],
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "number"},
                        "unit": {"type": "string"},
                        "flag": {"type": ["string", "null"]},
                    },
                },
            },
            "conclusion": {"type": ["string", "null"]},
        },
    },
    DocKind.PRESCRIPTION: {
        "name": "Prescription",
        "description": "处方：患者 + 药品列表 + 医嘱。",
        "type": "object",
        "additionalProperties": False,
        "required": ["patient_name", "medications"],
        "properties": {
            "patient_name": {"type": "string"},
            "medications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "dosage", "frequency"],
                    "properties": {
                        "name": {"type": "string"},
                        "dosage": {"type": "string"},
                        "frequency": {"type": "string"},
                    },
                },
            },
            "notes": {"type": ["string", "null"]},
        },
    },
}


def _patient_semantic(data: dict) -> list[str]:
    errs: list[str] = []
    if not 0 < data["age"] < 150:
        errs.append("语义: 年龄必须在 1~149 之间")
    if not data.get("symptoms"):
        errs.append("语义: 症状不能为空")
    contact = data.get("contact")
    if contact and not (contact.get("email") or contact.get("phone")):
        errs.append("语义: contact 至少要填 email 或 phone 之一")
    return errs


def _lab_semantic(data: dict) -> list[str]:
    errs: list[str] = []
    if not data.get("items"):
        errs.append("语义: 化验单至少要有 1 项指标")
    for i, item in enumerate(data.get("items", [])):
        if item["value"] < 0:
            errs.append(f"语义: items[{i}].value 不能为负")
    return errs


def _prescription_semantic(data: dict) -> list[str]:
    errs: list[str] = []
    if not data.get("medications"):
        errs.append("语义: 处方至少要有 1 个药品")
    for i, med in enumerate(data.get("medications", [])):
        if not med.get("dosage") or not med.get("frequency"):
            errs.append(f"语义: medications[{i}] 必须同时有 dosage 和 frequency")
    return errs


SEMANTIC_RULES: dict[DocKind, Callable[[dict], list[str]]] = {
    DocKind.PATIENT: _patient_semantic,
    DocKind.LAB: _lab_semantic,
    DocKind.PRESCRIPTION: _prescription_semantic,
}


# ═════════════════════════════════════════════════════════════════
# HTTP 层：纯标准库直连 OpenAI 兼容接口，全程只碰 JSON。
#   手拼请求体：顶层就是 messages + tools + tool_choice 三块并列（文档 §2.6）。
#   qwen 默认开 thinking 会限制 tool_choice 导致 400，必须显式关（文档 §3.1）。
# ═════════════════════════════════════════════════════════════════
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
MODEL = os.environ.get("OPENAI_MODEL", "qwen3.6-plus")
API_KEY = os.environ.get("OPENAI_API_KEY", "")
TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0"))
_raw_max_tokens = os.environ.get("OPENAI_MAX_TOKENS")
MAX_TOKENS = int(_raw_max_tokens) if _raw_max_tokens else None
MAX_RETRIES = int(os.environ.get("OPENAI_MAX_RETRIES", "2"))
QWEN_THINKING_OFF = "dashscope" in BASE_URL or "qwen" in MODEL.lower()


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


@dataclass
class RawResult:
    """生成层产出：json_str 为可解析的 JSON 字符串；为空时 note 说明原因。"""
    json_str: str | None
    note: str = ""


def _strip_json(content: str) -> str | None:
    """从文本里抠出第一个 JSON 对象，容忍 ```json 围栏和前导文本。"""
    text = content.strip()
    if text.startswith("```"):
        first, last = text.find("\n"), text.rfind("```")
        if first != -1 and last != -1 and last > first:
            text = text[first + 1:last].strip()
    s, e = text.find("{"), text.rfind("}")
    return text[s:e + 1] if s != -1 and e != -1 and e > s else None


def _base_payload(text: str) -> dict:
    p = {"model": MODEL, "messages": [{"role": "user", "content": text}], "temperature": TEMPERATURE}
    if MAX_TOKENS:
        p["max_tokens"] = MAX_TOKENS
    if QWEN_THINKING_OFF:
        p["enable_thinking"] = False
    return p


def build_tool_call_payload(text: str, schema: dict) -> dict:
    """§2.6 主通道：schema 装进 tools[].function.parameters，提示词零改动。"""
    p = _base_payload(text)
    p["tools"] = [{"type": "function", "function": {
        "name": schema["name"], "description": schema.get("description", ""), "parameters": schema}}]
    p["tool_choice"] = {"type": "function", "function": {"name": schema["name"]}}
    return p


def extract_json(payload: dict) -> RawResult:
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


# ═════════════════════════════════════════════════════════════════
# ② 路由：把"这是哪类文档"从抽取里独立出来。
#    能规则就不模型，能选择题就不填空题。低置信度不赌，转人工。
# ═════════════════════════════════════════════════════════════════
DEFAULT_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class RouteResult:
    """一次路由的结论。kind=None 表示无法确定（上游应走人工）。"""
    kind: DocKind | None
    confidence: float      # 0~1
    source: str            # "rule" | "model" | "none"
    reason: str


class RuleRouter:
    """关键词映射。只有唯一命中才下判断；零命中/多命中都交给模型。"""

    RULES: list[tuple[str, list[str]]] = [
        ("lab_report", ["血常规", "白细胞", "体温", "化验"]),
        ("prescription", ["剂量", "用法", "一日", "毫克", "处方"]),
        ("patient_record", ["症状", "咳嗽", "发烧", "门诊"]),
    ]

    def __init__(self, rules: list[tuple[str, list[str]]] | None = None) -> None:
        self.rules = rules or self.RULES

    def route(self, text: str) -> RouteResult | None:
        hits = [name for name, keywords in self.rules if any(k in text for k in keywords)]
        if len(hits) == 1:
            return RouteResult(DocKind(hits[0]), 1.0, "rule", f"关键词命中:{hits[0]}")
        return None


ROUTE_SCHEMA = {
    "name": "RouteChoice",
    "description": "路由选择题：判断输入是哪一类文档，并自评置信度(0~100)。",
    "type": "object",
    "additionalProperties": False,
    "required": ["kind", "confidence"],
    "properties": {
        "kind": {"type": "string", "enum": ["patient_record", "lab_report", "prescription"]},
        "confidence": {"type": "integer"},
    },
}


class ModelRouter:
    """纯 Python 版：手拼 RouteChoice 选择题请求，让模型只答『哪类 + 多自信』。
    畸形输出（枚举外值/字符串置信度/网络异常）一律归一化为 kind=None 转人工，不崩溃。"""

    def route(self, text: str) -> RouteResult:
        try:
            raw = extract_json(build_tool_call_payload(text, ROUTE_SCHEMA))
        except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError, IndexError) as exc:
            return RouteResult(None, 0.0, "model", f"路由调用异常: {type(exc).__name__}")
        if not raw.json_str:
            return RouteResult(None, 0.0, "model", raw.note or "路由未返回选择题答案")
        try:
            args = json.loads(raw.json_str)
            if not isinstance(args, dict):
                return RouteResult(None, 0.0, "model", "路由未返回选择题答案")
            kind = DocKind(args.get("kind"))
            conf_raw = args.get("confidence")
            conf = (float(conf_raw) if isinstance(conf_raw, (int, float)) else 0.0) / 100
            return RouteResult(kind, min(max(conf, 0.0), 1.0), "model", f"模型置信度{conf:.0%}")
        except (ValueError, TypeError, json.JSONDecodeError):
            return RouteResult(None, 0.0, "model", "路由输出非法，转人工")


class Router:
    """规则优先；规则判不出交给模型选择题；低置信度直接标人工（不赌）。"""

    def __init__(
        self,
        rule_router: RuleRouter | None = None,
        model_router: ModelRouter | None = None,
        *,
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.rule_router = rule_router or RuleRouter()
        self.model_router = model_router
        self.threshold = threshold

    def route(self, text: str) -> RouteResult:
        by_rule = self.rule_router.route(text)
        if by_rule is not None:
            return by_rule
        if self.model_router is None:
            return RouteResult(None, 0.0, "none", "无模型路由，且规则无法判定")
        result = self.model_router.route(text)
        if result.kind is not None and result.confidence < self.threshold:
            return RouteResult(None, result.confidence, "model",
                               f"低置信度({result.confidence:.0%})不赌，转人工")
        return result


# ═════════════════════════════════════════════════════════════════
# ③ 抽取：对选中的单一 schema 做结构化抽取，一次只干一件事。
# ═════════════════════════════════════════════════════════════════
class SchemaExtractor:
    """纯 Python 版单一 schema 抽取器：每类文档一个实例。"""

    def __init__(self, schema: dict) -> None:
        self.schema = schema

    def extract(self, text: str) -> RawResult:
        try:
            return extract_json(build_tool_call_payload(text, self.schema))
        except (urllib.error.URLError, OSError) as exc:
            return RawResult(None, f"网络/HTTP 异常: {type(exc).__name__}")
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            # 200 但响应体不是合法 JSON / 缺 choices[0].message -> 归一化进重试兜底
            return RawResult(None, f"响应解析异常: {type(exc).__name__}")


_GOOD_BY_KIND: dict[DocKind, dict] = {
    DocKind.PATIENT: {
        "name": "张三",
        "age": 32,
        "symptoms": ["发热", "咳嗽"],
        "risk_level": "high",
        "contact": {"phone": "13800000000"},
    },
    DocKind.LAB: {
        "patient_name": "张三",
        "items": [{"name": "白细胞", "value": 12.3, "unit": "10^9/L", "flag": "偏高"}],
        "conclusion": "白细胞偏高",
    },
    DocKind.PRESCRIPTION: {
        "patient_name": "张三",
        "medications": [{"name": "阿莫西林", "dosage": "500mg", "frequency": "一日两次"}],
        "notes": "饭后服用",
    },
}

_BAD_BY_KIND: dict[DocKind, dict] = {
    DocKind.PATIENT: {"name": "张三", "age": 32, "symptoms": []},
    DocKind.LAB: {"patient_name": "张三", "items": []},
    DocKind.PRESCRIPTION: {"patient_name": "张三", "medications": []},
}


class FakeExtractor:
    """脚本化抽取器：mode 控制失败剧本，离线覆盖流水线所有分支。"""

    def __init__(self, mode: str = "good", kind: DocKind | None = None) -> None:
        self.mode = mode
        self.kind = kind

    def bind(self, kind: DocKind) -> "FakeExtractor":
        return FakeExtractor(self.mode, kind)

    def extract(self, text: str, kind: DocKind | None = None) -> RawResult:
        kind = kind or self.kind
        if kind is None:
            return RawResult(None, "FakeExtractor: kind 未绑定")
        good = RawResult(json.dumps(_GOOD_BY_KIND[kind], ensure_ascii=False))
        if self.mode == "good":
            return good
        if self.mode == "retry_once":
            if "未通过校验" in text:
                return good
            return RawResult(json.dumps(_BAD_BY_KIND[kind], ensure_ascii=False))
        if self.mode == "hopeless":
            return RawResult(json.dumps(_BAD_BY_KIND[kind], ensure_ascii=False))
        return RawResult(None, "抱歉，我只能返回纯文本。")


# ═════════════════════════════════════════════════════════════════
# ④ 两层校验：格式层(手写 _check) + 语义层(业务规则)。
#    _check() 等价于 Pydantic model_validate()（strict 模式，对应 prod_singlefile 里
#    Field(strict=True) 的那份严格）在这套 schema 上做的检查：
#    必填字段齐全、类型正确、枚举合法、无多余字段(additionalProperties:false)。
#    语义规则管"业务合不合理"：格式不合法就不往下跑语义。
# ═════════════════════════════════════════════════════════════════
def _match_type(value: Any, t: str) -> bool:
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return type(value) is int                      # type is 排除 bool
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "null":
        return value is None
    return True


def _check(data: Any, schema: dict, path: str = "root") -> list[str]:
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
        items_schema = schema.get("items")
        if items_schema:                                   # 无 items 约束就不递归
            for i, item in enumerate(data):
                errors += _check(item, items_schema, f"{path}[{i}]")
    if "enum" in schema and data not in schema["enum"]:  # 枚举合法性
        errors.append(f"{path}: 枚举值 {data!r} 不在 {schema['enum']}")
    return errors


def schema_errors(schema: dict, data: dict) -> list[str]:
    """格式层：手写 _check() 等价于 Pydantic model_validate()。"""
    return _check(data, schema)


def semantic_errors(kind: DocKind, data: dict) -> list[str]:
    rule = SEMANTIC_RULES.get(kind)
    return rule(data) if rule is not None else []


def collect_errors(kind: DocKind, schema: dict, data: dict) -> list[str]:
    """两层合并：先格式后语义；格式不合法就不往下跑语义。"""
    fmt = schema_errors(schema, data)
    if fmt:
        return fmt
    return semantic_errors(kind, data)


def parse_or_error(raw_json: str | None, note: str = "") -> tuple[dict | None, list[str]]:
    if not raw_json:
        return None, [note or "模型未返回可解析的 JSON"]
    try:
        return json.loads(raw_json), []
    except json.JSONDecodeError as exc:
        return None, [f"JSON 语法错误: {exc}"]


# ═════════════════════════════════════════════════════════════════
# ⑤ 闭环：路由 -> 分流(人工/继续) -> 抽取 -> 两层校验 -> 重试 -> fallback/人工。
#    status 语义："ok" 正常解析 | "fallback" 业务兜底 | "human_review" 人工队列。
# ═════════════════════════════════════════════════════════════════
FIX_TEMPLATE = (
    "\n\n【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】\n{error}"
)


@dataclass
class ProdAttempt:
    """一次 invoke 的完整轨迹。"""
    kind: DocKind | None
    route: RouteResult
    status: str
    attempts_used: int
    errors: list[str]
    latency_ms: int


class ProductionPipeline:
    def __init__(
        self,
        router: Router,
        extractors: dict[DocKind, Any],
        *,
        max_retries: int = 2,
        fallbacks: dict[DocKind, dict] | None = None,
        metrics: "ProdMetrics | None" = None,
    ) -> None:
        self.router = router
        self.extractors = extractors
        self.max_retries = max_retries
        self.fallbacks = fallbacks or {}
        self.metrics = metrics or ProdMetrics()

    def invoke(self, text: str) -> tuple[dict | None, ProdAttempt]:
        started = time.perf_counter()
        route = self.router.route(text)
        self.metrics.record_route(route.source, route.confidence)

        # 路由分流：Router 已把低置信度归一化为 kind=None，这里定不了就走人工，不赌
        if route.kind is None:
            self.metrics.record_human()
            return None, ProdAttempt(
                route.kind, route, "human_review", 0, [route.reason],
                self._ms(started),
            )

        kind = route.kind
        extractor = self.extractors[kind]
        schema = SCHEMA_BY_KIND[kind]
        errors: list[str] = []
        for attempt in range(1, self.max_retries + 2):
            prompt = text if attempt == 1 else text + FIX_TEMPLATE.format(error=errors[-1])
            raw = extractor.extract(prompt)
            data, parse_errs = parse_or_error(raw.json_str, raw.note)
            if parse_errs:
                self.metrics.record_validation(ok=False)
                errors.extend(parse_errs)
                continue
            errs = collect_errors(kind, schema, data)
            if errs:
                self.metrics.record_validation(ok=False)
                errors.extend(errs)
                continue
            self.metrics.record_validation(ok=True)
            self.metrics.record_result(ok=True, attempts_used=attempt)
            return data, ProdAttempt(kind, route, "ok", attempt, errors, self._ms(started))

        # 重试耗尽：按 kind 的业务 fallback（区别于"ok"）；没有 fallback 就标人工
        self.metrics.record_result(ok=False, attempts_used=self.max_retries + 1)
        fallback = self.fallbacks.get(kind)
        if fallback is None:
            self.metrics.record_human()
            return None, ProdAttempt(
                kind, route, "human_review", self.max_retries + 1,
                errors or ["重试耗尽"], self._ms(started),
            )
        return fallback, ProdAttempt(
            kind, route, "fallback", self.max_retries + 1,
            errors or ["重试耗尽"], self._ms(started),
        )

    @staticmethod
    def _ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)


# ═════════════════════════════════════════════════════════════════
# ⑥ 观测：按环节分桶计数，定位"谁在拖后腿"。
# ═════════════════════════════════════════════════════════════════
class ProdMetrics:
    """环节分桶指标：success_rate 低时看 route_source / validation_failures 定位。"""

    def __init__(self) -> None:
        self.total = 0
        self.ok = 0
        self.human = 0
        self.fallback = 0
        self.retries_used = 0
        self.route_source: dict[str, int] = {}
        self.low_confidence = 0
        self.validation_failures = 0

    def record_route(self, source: str, confidence: float) -> None:
        self.route_source[source] = self.route_source.get(source, 0) + 1
        if confidence < DEFAULT_CONFIDENCE_THRESHOLD:
            self.low_confidence += 1

    def record_validation(self, *, ok: bool) -> None:
        if not ok:
            self.validation_failures += 1

    def record_human(self) -> None:
        self.human += 1

    def record_result(self, *, ok: bool, attempts_used: int) -> None:
        self.total += 1
        self.retries_used += attempts_used - 1
        if ok:
            self.ok += 1
        else:
            self.fallback += 1

    def summary(self) -> dict[str, Any]:
        rate = round(self.ok / self.total * 100, 2) if self.total else 0.0
        return {
            "total": self.total,
            "ok": self.ok,
            "human_review": self.human,
            "fallback": self.fallback,
            "retries_used": self.retries_used,
            "validation_failures": self.validation_failures,
            "route_source": self.route_source,
            "low_confidence": self.low_confidence,
            "success_rate_%": rate,
        }


# ═════════════════════════════════════════════════════════════════
# ⑦ 入口：离线演示 + 真实调用 + --dry-run 打印请求体。
# ═════════════════════════════════════════════════════════════════
DEFAULT_FALLBACKS = {
    DocKind.PATIENT: {"name": "", "age": 0, "symptoms": [], "risk_level": "low"},
    DocKind.LAB: {"patient_name": "", "items": []},
    DocKind.PRESCRIPTION: {"patient_name": "", "medications": []},
}


class FakeModelRouter:
    """脚本化模型路由：只覆盖低置信度/模棱两可两条路，让离线演示跑通全流程。"""

    def route(self, text: str) -> RouteResult:
        if "天气" in text:
            return RouteResult(None, 0.3, "model", "低置信度(30%)不赌，转人工")
        if "复杂" in text or "进一步" in text:
            return RouteResult(DocKind.PRESCRIPTION, 0.9, "model", "模型判为处方")
        return RouteResult(DocKind.PATIENT, 0.85, "model", "模型判为病历")


SAMPLES = {
    "病历·规则命中": "患者张三，32岁，发热咳嗽，评估高风险，电话13800000000",
    "化验单·规则命中": "患者李四，化验显示白细胞偏高，体温39度",
    "处方·规则命中": "开具处方，阿莫西林500mg，一日两次，饭后服用",
    "模棱两可·走模型选择题": "这位病人情况复杂，需进一步检查",
    "低置信度·转人工": "今天天气不错，适合出门散步",
}


def _make_fake_pipeline(fake_mode: str) -> tuple[ProductionPipeline, ProdMetrics]:
    metrics = ProdMetrics()
    router = Router(RuleRouter(), FakeModelRouter(), threshold=DEFAULT_CONFIDENCE_THRESHOLD)
    fake = FakeExtractor(fake_mode)
    extractors = {kind: fake.bind(kind) for kind in DocKind}
    pipeline = ProductionPipeline(
        router, extractors, max_retries=MAX_RETRIES,
        fallbacks=DEFAULT_FALLBACKS, metrics=metrics,
    )
    return pipeline, metrics


def _run_case(pipeline: ProductionPipeline, label: str, text: str) -> None:
    print(f"\n=== {label} ===")
    print(f"输入: {text[:50]}")
    obj, attempt = pipeline.invoke(text)
    print(
        f"route={attempt.route.source}:{attempt.route.reason}  "
        f"kind={attempt.kind.value if attempt.kind else None}  "
        f"status={attempt.status}  attempts={attempt.attempts_used}  "
        f"latency={attempt.latency_ms}ms"
    )
    for err in attempt.errors[:3]:
        print(f"  [err] {err[:120]}")
    print(f"结果: {obj}")


def run_fake_demo() -> None:
    print("############ 路径 1：一路顺利（good）############")
    pipeline, metrics = _make_fake_pipeline("good")
    for label, text in SAMPLES.items():
        _run_case(pipeline, label, text)
    print(f"\n计数: {metrics.summary()}")

    print("\n\n############ 路径 2：校验失败一次后自修复（retry_once）############")
    pipeline, _ = _make_fake_pipeline("retry_once")
    _run_case(pipeline, "病历·首次校验失败", SAMPLES["病历·规则命中"])
    print("\n\n############ 路径 3：重试耗尽走业务兜底（hopeless）############")
    pipeline, _ = _make_fake_pipeline("hopeless")
    _run_case(pipeline, "病历·反复校验失败", SAMPLES["病历·规则命中"])


def run_real_demo() -> None:
    metrics = ProdMetrics()
    router = Router(RuleRouter(), ModelRouter(), threshold=DEFAULT_CONFIDENCE_THRESHOLD)
    extractors = {kind: SchemaExtractor(SCHEMA_BY_KIND[kind]) for kind in DocKind}
    pipeline = ProductionPipeline(
        router, extractors, max_retries=MAX_RETRIES,
        fallbacks=DEFAULT_FALLBACKS, metrics=metrics,
    )
    for label, text in SAMPLES.items():
        _run_case(pipeline, label, text)
    print(f"\n计数: {metrics.summary()}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description="生产级结构化输出流水线（纯 Python 版，无 LangChain）")
    parser.add_argument("--fake", action="store_true", help="离线演示（无需 API key）")
    parser.add_argument("--dry-run", action="store_true", help="只打印请求体，不发请求")
    args = parser.parse_args()

    if args.dry_run:
        # 教学：先把「发给模型的请求体」摊开——路由选择题 + 抽取各一份
        print("=== 路由选择题请求体（让模型做『哪类文档』判断）===")
        print(json.dumps(build_tool_call_payload(SAMPLES["模棱两可·走模型选择题"], ROUTE_SCHEMA),
                         ensure_ascii=False, indent=2))
        print("\n=== 抽取请求体（以病历为例，实际按路由结果选对应 schema）===")
        print(json.dumps(build_tool_call_payload(SAMPLES["病历·规则命中"], SCHEMA_BY_KIND[DocKind.PATIENT]),
                         ensure_ascii=False, indent=2))
        print("\n[dry-run] 未发送请求。")
        return

    if args.fake:
        run_fake_demo()
    else:
        if not API_KEY:
            print("[警告] 未设置 OPENAI_API_KEY，真实调用会失败。可先用 --dry-run 看请求体。")
        run_real_demo()


if __name__ == "__main__":
    main()
# [AGC:END]
