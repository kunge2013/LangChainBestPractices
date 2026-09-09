# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""三类文档 schema + DocKind 枚举 + 语义规则表。

每类文档一个 Pydantic 模型，`extra="forbid"` 逼模型严格按 schema 输出。
语义规则（SEMANTIC_RULES）是"业务层校验"：schema 校验管格式，它管合不合理。
"""
from enum import Enum
from typing import Callable

from pydantic import BaseModel, ConfigDict

# [AGC:START] tool=Cc author=fangkun
class DocKind(str, Enum):
    """文档类型，同时也是路由的"选择题答案"。"""
    PATIENT = "patient_record"
    LAB = "lab_report"
    PRESCRIPTION = "prescription"


class RiskLevel(str, Enum):
    """病历：风险等级枚举。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContactInfo(BaseModel):
    """病历：嵌套联系方式。"""
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
    flag: str | None = None        # 偏高/偏低/正常 标记


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


# ─────────────────────────────────────────────────────────────────
# 语义规则：业务层校验（格式合法 ≠ 业务合理）。
# 每个 kind 一个函数，入参是已通过 schema 校验的模型实例。
# ─────────────────────────────────────────────────────────────────
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
# [AGC:END]
