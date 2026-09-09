# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""两层校验：格式层（schema） + 语义层（业务规则）。

- schema_errors   第一层：Pydantic model_validate 管"字段齐不齐、类型对不对"
- semantic_errors 第二层：SEMANTIC_RULES 管"业务合不合理"（年龄 200 岁、处方没药名）
- collect_errors  两层合并；任何一层出错都会被 pipeline 喂回 prompt 重试
"""
import json
from typing import Any

from pydantic import BaseModel, ValidationError

from .schemas import SEMANTIC_RULES, SCHEMA_BY_KIND, DocKind

# [AGC:START] tool=Cc author=fangkun
def schema_errors(model_cls: type[BaseModel], data: dict) -> list[str]:
    """格式层：返回 Pydantic 校验错误列表；空列表 = 通过。"""
    try:
        model_cls.model_validate(data)
        return []
    except ValidationError as exc:
        return [
            f"{'.'.join(str(p) for p in e['loc']) or 'root'}: {e['msg']}"
            for e in exc.errors()
        ]


def semantic_errors(kind: DocKind, obj: BaseModel) -> list[str]:
    """语义层：按 kind 跑业务规则；空列表 = 通过。"""
    rule = SEMANTIC_RULES.get(kind)
    return rule(obj) if rule is not None else []


def collect_errors(kind: DocKind, model_cls: type[BaseModel], data: dict) -> list[str]:
    """两层合并：先格式后语义；格式不合法就不往下跑语义。"""
    fmt = schema_errors(model_cls, data)
    if fmt:
        return fmt
    return semantic_errors(kind, model_cls.model_validate(data))


def parse_or_error(raw_json: str | None, note: str = "") -> tuple[dict | None, list[str]]:
    """把 RawResult.json_str 解析为 dict；返回 (data, errors)。"""
    if not raw_json:
        return None, [note or "模型未返回可解析的 JSON"]
    try:
        return json.loads(raw_json), []
    except json.JSONDecodeError as exc:
        return None, [f"JSON 语法错误: {exc}"]
# [AGC:END]
