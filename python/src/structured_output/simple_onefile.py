# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""单文件教学版：把「结构化输出最小可靠闭环」压缩到一个文件，便于理解。

与生产版（pipeline / extractors / observability / schemas / config 多文件）逻辑等价，
但去掉跨文件抽象，把五层保证平铺在这里：

  ① 数据模型  PatientRecord（Pydantic）——模型要输出的结构
  ② 生成层    extract()：把模型输出规范化为「JSON 字符串 or 失败说明」
  ③ 校验层    validate()：语法层 json.loads + Schema 层 Pydantic 校验
  ④ 修复层    FIX_TEMPLATE：校验失败时把错误喂回 prompt 让模型自纠正
  ⑤ 兜底+观测 重试耗尽返回 fallback + JSONL 日志

运行（在仓库 python/ 目录下执行，需配 OPENAI_* 环境变量）：
  python -m src.structured_output.simple_onefile
"""
import json
import os
import sys
import time
import uuid
from enum import Enum
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field

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


# ═════════════════════════════════════════════════════════════════
# ② 生成层：把模型输出规范化为「JSON 字符串 or 失败说明」。
#    with_structured_output(include_raw=True) 返回 {"raw", "parsed", "parsing_error"}，
#    JSON 从 raw.tool_calls[0].args（function_calling）或 raw.content（json_mode）里取。
# ═════════════════════════════════════════════════════════════════
class RawResult:
    def __init__(self, json_str: str | None, note: str = ""):
        self.json_str = json_str   # 可解析的 JSON 字符串；None 表示没产出 JSON
        self.note = note           # 失败原因


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


# ═════════════════════════════════════════════════════════════════
# ③ 校验层：语法层 json.loads + Schema 层 Pydantic 严格校验。
#    任何一层失败都抛错，交给 ④ 重试。
# ═════════════════════════════════════════════════════════════════
def validate(raw: RawResult, schema: type[BaseModel]) -> BaseModel:
    if not raw.json_str:
        raise ValueError(raw.note or "模型未返回可解析的 JSON")
    data = json.loads(raw.json_str)      # 语法层
    return schema.model_validate(data)   # Schema 层（strict 由 Field 控制）


# ═════════════════════════════════════════════════════════════════
# ④ 修复层 + ⑤ 兜底层：核心闭环。
#    每次失败把「上次校验错误」喂回 prompt（FIX_TEMPLATE），最多重试 max_retries 次，
#    耗尽后返回 fallback（默认 None）。
#    观测与流程解耦：流程里只把日志「攒成变量」（records 列表，纯数据不碰 IO），
#    流程结束后才统一 write_records() 落盘——IO 完全独立于控制流。
# ═════════════════════════════════════════════════════════════════
FIX_TEMPLATE = "\n\n【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】\n{error}"
LOG_FILE = "logs/simple_onefile.jsonl"


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
        "status": status,
        "attempt": attempt,
        "error": error[:400],
        "prompt": prompt,
        "raw_json": raw.json_str,
        "parsed": parsed,
    }


def write_records(records: list[dict]) -> None:
    """把攒好的日志统一写入 JSONL：IO 与流程完全分离。"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ═════════════════════════════════════════════════════════════════
# 入口：真实调用（读 OPENAI_* 环境变量）
# ═════════════════════════════════════════════════════════════════
def build_llm() -> ChatOpenAI:
    base_url = os.environ.get("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
    model = os.environ.get("OPENAI_MODEL", "qwen3.6-plus")
    # qwen 默认开 thinking，会限制 tool_choice 导致结构化输出 400，必须显式关
    extra = {"enable_thinking": False} if ("dashscope" in base_url or "qwen" in model.lower()) else None
    return ChatOpenAI(model=model, base_url=base_url,
                      api_key=os.environ.get("OPENAI_API_KEY"),
                      temperature=0, **(extra or {}))


SAMPLES = {
    "完整病历": "患者老八，100岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13333333333。",
    # "信息缺失": "一个发烧的病人。",
    # "无关内容": "今天天气不错，适合出门散步。",
}


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    load_dotenv(override=True)
    # 必须显式传 method：langchain-openai 1.4+ 默认已是 json_schema（仅 OpenAI/Claude/Gemini
    # 支持），deepseek/qwen 不传会 400。function_calling 对二者最稳，见文档 §2.2/§7。
    llm = build_llm().with_structured_output(PatientRecord, method="function_calling", include_raw=True)
    extract = lambda t: extract_real(t, llm)                          # noqa: E731

    for label, text in SAMPLES.items():
        print(f"\n=== {label} ===")
        obj, attempt, errors, records = run_pipeline(text, extract, PatientRecord, max_retries=2)
        print(f"attempts={attempt}  结果={obj.model_dump() if obj else None}")
        for err in errors:
            print(f"  [err] {err[:160]}")


if __name__ == "__main__":
    main()
# [AGC:END]
