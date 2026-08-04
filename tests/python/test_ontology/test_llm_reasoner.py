# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
import pytest
import json
from unittest.mock import Mock, MagicMock
from ontology.llm_reasoner import OntologyLLMReasoner


class FakeMessage:
    """A fake LLM message for testing without langchain imports."""
    def __init__(self, content: str):
        self.content = content


@pytest.fixture
def mock_llm():
    """Create mock LLM"""
    llm = Mock()
    llm.invoke = MagicMock()
    return llm


def test_reason_concept_city(mock_llm):
    """测试城市概念推理"""
    response_data = {
        "instances": [
            {"name": "上海", "code": "021", "reason": "上海是四大一线城市之一"},
            {"name": "北京", "code": "010", "reason": "北京是政治中心"}
        ],
        "confidence": 0.95
    }
    mock_llm.invoke.return_value = FakeMessage(json.dumps(response_data, ensure_ascii=False))

    reasoner = OntologyLLMReasoner(mock_llm)
    result = reasoner.reason_concept("tier1_cities", "city")

    assert isinstance(result, list)
    assert len(result) == 2
    assert "上海" in result
    assert "北京" in result


def test_reason_concept_with_context(mock_llm):
    """测试带上下文的概念推理"""
    response_data = {"instances": [{"name": "杭州", "code": "0571"}], "confidence": 0.8}
    mock_llm.invoke.return_value = FakeMessage(json.dumps(response_data, ensure_ascii=False))

    reasoner = OntologyLLMReasoner(mock_llm)
    result = reasoner.reason_concept("new_cities", "city", context={"region": "华东"})

    assert isinstance(result, list)
    assert "杭州" in result


def test_reason_concept_invalid_json(mock_llm):
    """测试无效JSON响应"""
    mock_llm.invoke.return_value = FakeMessage("invalid json")

    reasoner = OntologyLLMReasoner(mock_llm)
    result = reasoner.reason_concept("test", "city")

    assert result == []


def test_reason_concept_empty_instances(mock_llm):
    """测试空实例列表"""
    response_data = {"instances": [], "confidence": 0.5}
    mock_llm.invoke.return_value = FakeMessage(json.dumps(response_data))

    reasoner = OntologyLLMReasoner(mock_llm)
    result = reasoner.reason_concept("test", "city")

    assert result == []


def test_build_reasoning_prompt():
    """测试推理提示词构建"""
    reasoner = OntologyLLMReasoner(Mock())
    prompt = reasoner._build_reasoning_prompt()

    assert "抽象概念" in prompt
    assert "概念分类" in prompt
