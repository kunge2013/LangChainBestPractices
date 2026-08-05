# [AGC:FILE] tool=Cc author=fangkun date=2026-08-04
"""
LLM推理引擎：当数据库未命中时，使用LLM进行概念推理
"""

# [AGC:START] tool=Cc author=fangkun
import json
import logging
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class OntologyLLMReasoner:
    """
    LLM推理引擎

    当数据库未命中时，使用LLM进行概念推理
    """

    def __init__(self, model):
        """
        初始化推理引擎

        参数:
            model: LangChain Chat模型（任意兼容ChatOpenAI接口的模型）
        """
        self.model = model
        self.reasoning_prompt = self._build_reasoning_prompt()

    def _build_reasoning_prompt(self) -> str:
        """
        构建推理提示词模板

        返回:
            提示词字符串
        """
        return """你是一个业务知识推理专家。给定一个抽象概念，请推理出其包含的具体实例列表。

概念名称：{concept_name}
概念分类：{concept_category}
上下文：{context}

请返回JSON格式：
{{
  "instances": [
    {{"name": "上海", "code": "021", "reason": "上海是公认的四大一线城市之一"}},
    {{"name": "北京", "code": "010", "reason": "北京是政治中心，属于一线城市"}}
  ],
  "confidence": 0.95
}}

注意：
1. 只返回JSON格式，不要有其他文字
2. instances数组包含具体实例
3. code字段为物理编码（如城市区号），如果不确定可以省略
4. confidence表示推理置信度（0-1之间）
5. 根据概念分类进行推理（city返回城市，customer返回公司名等）
"""

    def reason_concept(
        self,
        concept_name: str,
        concept_category: str,
        context: Dict = None
    ) -> List[str]:
        """
        LLM推理：给定抽象概念，推理出具体实例列表

        参数:
            concept_name: 概念名称（如"一线城市"）
            concept_category: 概念分类（city/customer/region）
            context: 额外上下文信息

        返回:
            推理出的实例名称列表
        """
        try:
            # 构建提示词
            prompt_text = self.reasoning_prompt.format(
                concept_name=concept_name,
                concept_category=concept_category,
                context=json.dumps(context, ensure_ascii=False) if context else "无"
            )

            # 调用LLM
            logger.info(f"触发LLM推理: {concept_name} ({concept_category})")
            response = self.model.invoke(prompt_text)
            response_text = response.content.strip()

            # 解析JSON响应
            try:
                # Strip markdown code blocks if present (```json ... ```)
                cleaned_text = response_text
                if cleaned_text.startswith("```"):
                    # Remove opening ```json or ```
                    first_newline = cleaned_text.find("\n")
                    if first_newline != -1:
                        cleaned_text = cleaned_text[first_newline + 1:]
                    # Remove closing ```
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-3]
                    cleaned_text = cleaned_text.strip()

                result = json.loads(cleaned_text)
                instances = result.get("instances", [])
                confidence = result.get("confidence", 0.0)

                logger.info(f"LLM推理完成: {len(instances)} 个实例, 置信度: {confidence}")

                # 提取实例名称
                return [inst["name"] for inst in instances if "name" in inst]

            except json.JSONDecodeError as e:
                logger.error(f"LLM响应JSON解析失败: {e}, 响应: {response_text}")
                return []

        except Exception as e:
            logger.error(f"LLM推理失败: {e}")
            return []
# [AGC:END]
