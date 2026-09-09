# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""生产级结构化输出流水线：路由与生成分离，两层校验，人工兜底。

核心架构（对应文档 §十二）：
  ① 规则路由 RuleRouter     能规则就不模型（关键词唯一命中）
  ② 模型路由 ModelRouter    模棱两可时让模型做"选择题"（枚举+置信度），低置信度走人工
  ③ 抽取   SchemaExtractor  对选中的单一 schema 做 with_structured_output，一次只干一件事
  ④ 校验   validate         两层：schema 格式层 + 语义业务层
  ⑤ 闭环   ProductionPipeline 校验失败带具体错误重试，耗尽给业务 fallback 或人工队列

运行：
  离线演示：python -m src.structured_output.prod.demo --fake
  真实调用：python -m src.structured_output.prod.demo
  测试：    python -m pytest src/structured_output/prod/tests -q
"""
