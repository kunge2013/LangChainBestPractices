# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""生产级结构化输出·单文件版：路由与生成分离，两层校验，人工兜底。

把 prod/ 多文件版的逻辑平铺到一个文件，去掉跨文件抽象，便于理解（对应文档 §十二）：

  ① 数据模型  三类文档 schema + DocKind 枚举 + 语义规则（schemas.py）
  ② 路由      RuleRouter(规则优先) + ModelRouter(选择题+置信度) + Router(组合)
              规则唯一命中就判；模棱两可上交模型；低置信度不赌，转人工（router.py）
  ③ 抽取      SchemaExtractor(单 schema) + FakeExtractor(离线脚本)（extractor.py）
  ④ 校验      两层：schema 格式层(Pydantic) + 语义业务层（validate.py）
  ⑤ 闭环      ProductionPipeline：路由→分流→抽取→校验→重试→fallback/人工（pipeline.py）
  ⑥ 观测      ProdMetrics 按环节分桶计数（observability.py）

运行（在仓库 python/ 目录下；目录名以数字开头，不能 `python -m`，直接跑文件）：
  离线演示（无需 key）：python src/base_practice/20_prod_structured_output/prod_singlefile.py --fake
  真实调用：python src/base_practice/20_prod_structured_output/prod_singlefile.py
  测试：python -m pytest src/base_practice/20_prod_structured_output/tests -q
"""
import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# [AGC:START] tool=Cc author=fangkun
# ═════════════════════════════════════════════════════════════════
# ① 数据模型：每类文档一个 Pydantic 模型 + DocKind 枚举 + 语义规则表。
#    extra="forbid" -> additionalProperties:false（模型多输出字段即判失败）
#    语义规则(SEMANTIC_RULES)是"业务层校验"：schema 校验管格式，它管合不合理。
# ═════════════════════════════════════════════════════════════════
class DocKind(str, Enum):
    """文档类型，同时也是路由的"选择题答案"。"""
    PATIENT = "patient_record"
    LAB = "lab_report"
    PRESCRIPTION = "prescription"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    phone: str | None = None


class PatientRecord(BaseModel):
    """病历：患者信息 + 症状 + 风险评估。"""
    model_config = ConfigDict(extra="forbid")

    name: str
    age: int
    symptoms: list[str]
    risk_level: RiskLevel
    contact: ContactInfo | None = None


class LabItem(BaseModel):
    """化验单：单条检验指标。"""
    model_config = ConfigDict(extra="forbid")

    name: str
    value: float
    unit: str
    flag: str | None = None


class LabReport(BaseModel):
    """化验单：患者 + 指标列表 + 结论。"""
    model_config = ConfigDict(extra="forbid")

    patient_name: str
    items: list[LabItem]
    conclusion: str | None = None


class Medication(BaseModel):
    """处方：单个药品 + 剂量 + 频次。"""
    model_config = ConfigDict(extra="forbid")

    name: str
    dosage: str
    frequency: str


class Prescription(BaseModel):
    """处方：患者 + 药品列表 + 医嘱。"""
    model_config = ConfigDict(extra="forbid")

    patient_name: str
    medications: list[Medication]
    notes: str | None = None


SCHEMA_BY_KIND: dict[DocKind, type[BaseModel]] = {
    DocKind.PATIENT: PatientRecord,
    DocKind.LAB: LabReport,
    DocKind.PRESCRIPTION: Prescription,
}


def _patient_semantic(obj: PatientRecord) -> list[str]:
    errs: list[str] = []
    if not 0 < obj.age < 150:
        errs.append("语义: 年龄必须在 1~149 之间")
    if not obj.symptoms:
        errs.append("语义: 症状不能为空")
    if obj.contact and not (obj.contact.email or obj.contact.phone):
        errs.append("语义: contact 至少要填 email 或 phone 之一")
    return errs


def _lab_semantic(obj: LabReport) -> list[str]:
    errs: list[str] = []
    if not obj.items:
        errs.append("语义: 化验单至少要有 1 项指标")
    for i, item in enumerate(obj.items):
        if item.value < 0:
            errs.append(f"语义: items[{i}].value 不能为负")
    return errs


def _prescription_semantic(obj: Prescription) -> list[str]:
    errs: list[str] = []
    if not obj.medications:
        errs.append("语义: 处方至少要有 1 个药品")
    for i, med in enumerate(obj.medications):
        if not med.dosage or not med.frequency:
            errs.append(f"语义: medications[{i}] 必须同时有 dosage 和 frequency")
    return errs


SEMANTIC_RULES: dict[DocKind, Callable[[BaseModel], list[str]]] = {
    DocKind.PATIENT: _patient_semantic,
    DocKind.LAB: _lab_semantic,
    DocKind.PRESCRIPTION: _prescription_semantic,
}


# ═════════════════════════════════════════════════════════════════
# ② 路由：把"这是哪类文档"从抽取里独立出来。
#    能规则就不模型，能选择题就不填空题。
#    ModelRouter 优先用 Pydantic 校验过的 parsed；畸形输出归一化为 kind=None 转人工。
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


class RouteChoice(BaseModel):
    """路由"选择题"的 schema：只要一个答案 + 自评置信度。"""
    model_config = ConfigDict(extra="forbid")

    kind: DocKind
    confidence: int = Field(ge=0, le=100)


class ModelRouter:
    """用 with_structured_output 让模型做选择题；优先取 parsed，raw 兜底解析。"""

    def __init__(self, llm: Any, *, method: str = "function_calling") -> None:
        self._runnable = llm.with_structured_output(
            RouteChoice, method=method, include_raw=True
        )

    def route(self, text: str) -> RouteResult:
        try:
            res = self._runnable.invoke(text)
        except Exception as exc:                     # 网络/解析异常也不能让整条请求崩溃
            return RouteResult(None, 0.0, "model", f"路由调用异常: {type(exc).__name__}")
        parsed = res.get("parsed")
        if isinstance(parsed, RouteChoice):
            return RouteResult(
                parsed.kind, parsed.confidence / 100, "model",
                f"模型置信度{parsed.confidence / 100:.0%}",
            )
        raw = res.get("raw")
        if raw is None:
            return RouteResult(None, 0.0, "model", "路由调用无原始输出")
        try:
            tool_calls = getattr(raw, "tool_calls", None)
            args = (
                tool_calls[0].get("args")
                if tool_calls and isinstance(tool_calls[0], dict)
                else None
            )
            if not isinstance(args, dict):
                return RouteResult(None, 0.0, "model", "路由未返回选择题答案")
            kind_raw, conf_raw = args.get("kind"), args.get("confidence")
            kind = DocKind(kind_raw) if isinstance(kind_raw, str) else None
            conf = (float(conf_raw) if isinstance(conf_raw, (int, float)) else 0.0) / 100
            if kind is None:
                return RouteResult(None, 0.0, "model", "路由未返回合法类型")
            return RouteResult(kind, min(max(conf, 0.0), 1.0), "model", f"模型置信度{conf:.0%}")
        except (ValueError, TypeError):
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
@dataclass
class RawResult:
    """抽取结果：json_str 为可解析的 JSON 字符串；为空时 note 说明原因。"""
    json_str: str | None
    note: str = ""


def pick_json(raw: BaseMessage) -> tuple[str | None, str]:
    """从 AIMessage 提取 JSON：function_calling 取 tool_calls[0].args，否则取 content。"""
    tool_calls = getattr(raw, "tool_calls", None)
    if tool_calls:
        args = tool_calls[0].get("args") if isinstance(tool_calls[0], dict) else None
        if isinstance(args, dict) and args:
            return json.dumps(args, ensure_ascii=False), ""
    content = getattr(raw, "content", None)
    if isinstance(content, str) and content.strip():
        text = content.strip()
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1], ""
        return None, "content 中未找到 JSON 对象"
    return None, "模型未返回工具调用或文本内容"


class SchemaExtractor:
    """单一 schema 的结构化抽取器：每类文档一个实例。"""

    def __init__(
        self,
        llm: Any,
        model_cls: type[BaseModel],
        *,
        method: str = "function_calling",
    ) -> None:
        self.model_cls = model_cls
        self._runnable = llm.with_structured_output(
            model_cls, method=method, include_raw=True
        )

    def extract(self, text: str) -> RawResult:
        res = self._runnable.invoke(text)
        raw = res.get("raw")
        if raw is None:
            return RawResult(None, "无原始输出")
        json_str, note = pick_json(raw)
        return RawResult(json_str, note)


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
# ④ 两层校验：格式层（Pydantic） + 语义层（业务规则）。
#    Pydantic 管"字段齐不齐、类型对不对"，语义规则管"业务合不合理"。
# ═════════════════════════════════════════════════════════════════
def schema_errors(model_cls: type[BaseModel], data: dict) -> list[str]:
    try:
        model_cls.model_validate(data)
        return []
    except ValidationError as exc:
        return [
            f"{'.'.join(str(p) for p in e['loc']) or 'root'}: {e['msg']}"
            for e in exc.errors()
        ]


def semantic_errors(kind: DocKind, obj: BaseModel) -> list[str]:
    rule = SEMANTIC_RULES.get(kind)
    return rule(obj) if rule is not None else []


def collect_errors(kind: DocKind, model_cls: type[BaseModel], data: dict) -> list[str]:
    """两层合并：先格式后语义；格式不合法就不往下跑语义。"""
    fmt = schema_errors(model_cls, data)
    if fmt:
        return fmt
    return semantic_errors(kind, model_cls.model_validate(data))


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
        fallbacks: dict[DocKind, BaseModel] | None = None,
        metrics: "ProdMetrics | None" = None,
    ) -> None:
        self.router = router
        self.extractors = extractors
        self.max_retries = max_retries
        self.fallbacks = fallbacks or {}
        self.metrics = metrics or ProdMetrics()

    def invoke(self, text: str) -> tuple[BaseModel | None, ProdAttempt]:
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

        kind, extractor, model_cls = (
            route.kind,
            self.extractors[route.kind],
            SCHEMA_BY_KIND[route.kind],
        )
        errors: list[str] = []
        for attempt in range(1, self.max_retries + 2):
            prompt = text if attempt == 1 else text + FIX_TEMPLATE.format(error=errors[-1])
            raw = extractor.extract(prompt)
            data, parse_errs = parse_or_error(raw.json_str, raw.note)
            if parse_errs:
                self.metrics.record_validation(ok=False)
                errors.extend(parse_errs)
                continue
            errs = collect_errors(kind, model_cls, data)
            if errs:
                self.metrics.record_validation(ok=False)
                errors.extend(errs)
                continue
            obj = model_cls.model_validate(data)
            self.metrics.record_validation(ok=True)
            self.metrics.record_result(ok=True, attempts_used=attempt)
            return obj, ProdAttempt(kind, route, "ok", attempt, errors, self._ms(started))

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
# ⑦ 入口：Provider 配置 + 离线演示 + 真实调用。
# ═════════════════════════════════════════════════════════════════
def _build_chat_model(provider: str = "auto") -> ChatOpenAI:
    """OpenAI 兼容接口（qwen/deepseek 均走 ChatOpenAI）。"""
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    model = os.environ.get("OPENAI_MODEL", "")
    if provider == "auto":
        provider = "deepseek" if ("deepseek" in model or "deepseek" in base_url) else "qwen"
    if provider == "deepseek":
        base_url = base_url or "https://api.deepseek.com"
        model = model or "deepseek-v4-flash"
        extra = None
    else:
        base_url = base_url or "https://coding.dashscope.aliyuncs.com/v1"
        model = model or "qwen3.6-plus"
        # qwen 默认开 thinking，会限制 tool_choice 导致结构化输出 400，必须显式关
        extra = {"enable_thinking": False}
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0")),
        # 自定义 body 参数（enable_thinking）必须走 extra_body：直接传会进 model_kwargs
        # -> payload 顶层，新版 openai SDK 强类型签名会抛 TypeError
        extra_body=extra,
    )


DEFAULT_FALLBACKS = {
    DocKind.PATIENT: PatientRecord(name="", age=0, symptoms=[], risk_level="low"),
    DocKind.LAB: LabReport(patient_name="", items=[]),
    DocKind.PRESCRIPTION: Prescription(patient_name="", medications=[]),
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
    router = Router(RuleRouter(), FakeModelRouter(), threshold=0.6)
    fake = FakeExtractor(fake_mode)
    extractors = {kind: fake.bind(kind) for kind in DocKind}
    pipeline = ProductionPipeline(
        router, extractors, max_retries=2, fallbacks=DEFAULT_FALLBACKS, metrics=metrics
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
    print(f"结果: {obj.model_dump() if obj else None}")


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


def run_real_demo(provider: str) -> None:
    llm = _build_chat_model(provider)
    metrics = ProdMetrics()
    router = Router(RuleRouter(), ModelRouter(llm), threshold=0.6)
    extractors = {
        kind: SchemaExtractor(llm, SCHEMA_BY_KIND[kind]) for kind in DocKind
    }
    pipeline = ProductionPipeline(
        router, extractors, max_retries=2, fallbacks=DEFAULT_FALLBACKS, metrics=metrics
    )
    for label, text in SAMPLES.items():
        _run_case(pipeline, label, text)
    print(f"\n计数: {metrics.summary()}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="生产级结构化输出流水线（单文件版）")
    parser.add_argument("--fake", action="store_true", help="离线演示（无需 API key）")
    parser.add_argument("--provider", default="auto", choices=["auto", "qwen", "deepseek"])
    args = parser.parse_args()

    if args.fake:
        run_fake_demo()
    else:
        run_real_demo(args.provider)


if __name__ == "__main__":
    main()
# [AGC:END]
