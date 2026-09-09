# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""演示 Schema：自由文本 -> 结构化病历抽取，刻意覆盖必填/可选/枚举/嵌套/类型五类校验点。"""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# [AGC:START] tool=Cc author=fangkun
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
    # 刻意不用全局 strict：str 枚举要在宽松模式下接受 "high" 这类值；
    # 类型强制转换的教学点只打在 age 等关键字段上（Field(strict=True)）。
    # extra="forbid"：模型多输出的字段会被判失败，逼模型严格按 schema 输出。
    model_config = ConfigDict(extra="forbid")

    name: str = Field(strict=True)
    age: int = Field(strict=True)
    symptoms: list[str]
    risk_level: RiskLevel
    contact: ContactInfo | None = None
# [AGC:END]
