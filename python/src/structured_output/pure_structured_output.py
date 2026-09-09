# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""纯 Python 实现「结构化输出最小可靠闭环」：不依赖 LangChain，仅用标准库 urllib 直连 OpenAI 兼容接口。

与 simple_onefile.py / 生产版（LangChain）逻辑等价，但把「发给模型的到底是什么」摊开在眼前：
请求体顶层就是 messages + tools + tool_choice 三块并列，schema 经 tools 通道发给模型，
提示词文本零改动——文档 §2.6 讲的机制在这里原样可见。

五层保证：
  ① 数据模型  SCHEMA（纯 dict JSON Schema，等价 Pydantic 的 PatientRecord.model_json_schema()）
  ② 生成层    extract()：手拼 HTTP 请求体 -> POST /chat/completions -> 取 tool_calls 或 content
  ③ 校验层    validate()：语法层 json.loads + Schema 层手写 _check()（必填/类型/枚举/禁多余字段）
  ④ 修复层    FIX_TEMPLATE：校验失败把错误喂回 prompt 重试
  ⑤ 兜底+观测  重试耗尽返回 None + records 收集日志、流程结束后统一写 JSONL

运行（仓库 python/ 目录下，配 OPENAI_BASE_URL / OPENAI_MODEL / OPENAI_API_KEY）：
  真实调用：python -m src.structured_output.pure_structured_output
  只看请求体（不发请求）：python -m src.structured_output.pure_structured_output --dry-run
  切换 json_mode 对比两条通道：python -m src.structured_output.pure_structured_output --method json_mode
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import uuid

from dotenv import load_dotenv

load_dotenv(override=True)   # 读仓库 python/.env（已被 gitignore），与其它脚本同一套配置

# [AGC:START] tool=Cc author=fangkun
# ═════════════════════════════════════════════════════════════════
# ① 数据模型：纯 dict 的 JSON Schema，等价于 Pydantic 的 PatientRecord.model_json_schema()。
#    Pydantic 类 -> 本 dict 的映射（对应文档 §2.6）：
#      class PatientRecord         -> "name": "PatientRecord"
#      类 docstring                -> "description"
#      ConfigDict(extra="forbid")  -> "additionalProperties": False
#      name/age/symptoms/risk_level -> "required"（可选字段不在此列）
#      name: str / age: int        -> "type": "string" / "integer"
#      symptoms: list[str]         -> "type":"array","items":{"type":"string"}
#      risk_level: RiskLevel       -> "enum": ["low","medium","high"]
#      contact: ContactInfo|None   -> "type":["object","null"]
# ═════════════════════════════════════════════════════════════════
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

# 环境配置（与仓库其它脚本同一套 OPENAI_* 变量）
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
MODEL = os.environ.get("OPENAI_MODEL", "qwen3.6-plus")
API_KEY = os.environ.get("OPENAI_API_KEY", "")
TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0"))
_raw_max_tokens = os.environ.get("OPENAI_MAX_TOKENS")
MAX_TOKENS = int(_raw_max_tokens) if _raw_max_tokens else None
MAX_RETRIES = int(os.environ.get("OPENAI_MAX_RETRIES", "2"))
# qwen 默认开 thinking，会限制 tool_choice 导致结构化输出 400，必须显式关（文档 §3.1）
QWEN_THINKING_OFF = "dashscope" in BASE_URL or "qwen" in MODEL.lower()


# ═════════════════════════════════════════════════════════════════
# HTTP 层：直接调用 OpenAI 兼容接口，全程只碰 JSON。
# ═════════════════════════════════════════════════════════════════
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


# ═════════════════════════════════════════════════════════════════
# ② 生成层：手拼请求体，把 schema 送进 tools / response_format 通道。
# ═════════════════════════════════════════════════════════════════
class RawResult:
    """生成层产出：json_str 为可解析的 JSON 字符串；None 表示没产出 JSON。"""

    def __init__(self, json_str: str | None, note: str = ""):
        self.json_str = json_str
        self.note = note


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


def build_function_calling_payload(text: str) -> dict:
    """§2.6 主通道：schema 装进 tools[].function.parameters，提示词零改动。"""
    p = _base_payload(text)
    p["tools"] = [{"type": "function", "function": {
        "name": SCHEMA["name"], "description": SCHEMA["description"], "parameters": SCHEMA}}]
    p["tool_choice"] = {"type": "function", "function": {"name": SCHEMA["name"]}}
    return p


def build_json_mode_payload(text: str) -> dict:
    """§2.6 对照通道：不发 tools，schema 必须写进 prompt（且含 "JSON" 字样）。"""
    p = _base_payload(text)
    p["messages"] = [
        {"role": "system", "content": "你只输出合法 JSON，且必须符合以下 JSON Schema：\n"
                                      + json.dumps(SCHEMA, ensure_ascii=False)},
        {"role": "user", "content": text},
    ]
    p["response_format"] = {"type": "json_object"}
    return p


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


# ═════════════════════════════════════════════════════════════════
# ③ 校验层：语法层 json.loads + Schema 层手写 _check()。
#    _check() 等价于 Pydantic model_validate() 在这套 schema 上做的检查：
#    必填字段齐全、类型正确、枚举合法、无多余字段（additionalProperties:false）。
# ═════════════════════════════════════════════════════════════════
def _match_type(value, t: str) -> bool:
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


# ═════════════════════════════════════════════════════════════════
# ④ 修复层 + ⑤ 兜底层：核心闭环（与 simple_onefile.py 相同的控制流）。
#    观测与流程解耦：流程里只把日志攒进 records，流程结束后统一 write_records()。
# ═════════════════════════════════════════════════════════════════
FIX_TEMPLATE = "\n\n【上一次输出未通过校验，请仅修复以下错误并重新输出 JSON】\n{error}"
LOG_FILE = "logs/pure_structured_output.jsonl"


def run(text: str, builder, *, fallback: dict | None = None):
    """返回 (解析结果 | fallback, 实际尝试次数, 错误列表, 日志记录列表)。"""
    errors: list[str] = []
    records: list[dict] = []                            # 日志先攒在这，流程跑完再统一写出
    last_prompt, last_raw = text, RawResult(None, "")
    started = time.perf_counter()
    for attempt in range(1, MAX_RETRIES + 2):
        # attempt=1 用原始文本；重试则追加错误反馈（修复层）
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
    # 重试耗尽：兜底层（fallback 可配置，默认 None）
    last = errors[-1] if errors else "重试耗尽"
    records.append(_record(MAX_RETRIES + 1, "fallback", last_prompt, last_raw, None, last, started))
    write_records(records)                              # 流程结束，统一落盘
    return fallback, MAX_RETRIES + 1, errors, records


def _record(attempt: int, status: str, prompt: str, raw: RawResult, parsed: dict | None,
            error: str, started: float) -> dict:
    """单条日志 = 纯数据（不碰 IO）。"""
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "request_id": uuid.uuid4().hex[:12],
        "status": status,
        "attempt": attempt,
        "error": error[:400],
        "prompt": prompt,
        "raw_json": raw.json_str,
        "parsed": parsed,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "provider": "openai-compatible",
        "model": MODEL,
        "method": METHOD,
    }


def write_records(records: list[dict]) -> None:
    """把攒好的日志统一写入 JSONL：IO 与流程完全分离。"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ═════════════════════════════════════════════════════════════════
# 入口
# ═════════════════════════════════════════════════════════════════
METHOD = "function_calling"

SAMPLES = {
    "完整病历": "患者张三，32岁，因发热咳嗽就诊，症状持续三天，评估为高风险，联系电话13800000000。",
    # "信息缺失": "一个发烧的病人。",
    # "无关内容": "今天天气不错，适合出门散步。",
}


def main() -> None:
    global METHOD
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description="纯 Python 结构化输出闭环（无 LangChain）")
    parser.add_argument("--method", default="function_calling",
                        choices=["function_calling", "json_mode"])
    parser.add_argument("--dry-run", action="store_true", help="只打印请求体，不发请求")
    args = parser.parse_args()

    METHOD = args.method
    builder = build_function_calling_payload if METHOD == "function_calling" else build_json_mode_payload

    # 教学：先把「发给模型的请求体」摊开——§2.6 讲的机制原样可见
    print(f"=== 请求体预览（method={METHOD}，实际发给 {BASE_URL}/chat/completions）===")
    print(json.dumps(builder(SAMPLES["完整病历"]), ensure_ascii=False, indent=2))
    if args.dry_run:
        print("\n[dry-run] 未发送请求。")
        return
    if not API_KEY:
        print("\n[警告] 未设置 OPENAI_API_KEY，真实调用会失败。可先用 --dry-run 看请求体。")

    for label, text in SAMPLES.items():
        print(f"\n=== {label} ===")
        obj, attempt, errors, records = run(text, builder)
        print(f"attempts={attempt}  结果={obj}")
        for err in errors:
            print(f"  [err] {err[:160]}")


if __name__ == "__main__":
    main()
# [AGC:END]
