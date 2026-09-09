# [AGC:FILE] tool=Cc author=fangkun date=2026-09-09
"""实践 20：生产级结构化输出——路由与生成分离 + 两层校验 + 人工兜底。

同一次实践中给出两个等价实现，便于对照「框架版 vs 纯标准库版」：

  prod_singlefile.py   LangChain 版：ChatOpenAI + Pydantic，单文件生产流水线
  prod_pure.py         纯 Python 版：urllib 直连 OpenAI 兼容接口，纯 dict JSON Schema

两者逻辑等价（RuleRouter 规则优先 → ModelRouter 选择题+置信度 → 低置信转人工
→ 单 schema 抽取 → 两层校验 → 重试 → fallback/人工），只是模型调用层不同。

目录名以数字开头，无法 `import`/`python -m`，请直接按文件名运行：
  cd python && python src/base_practice/20_prod_structured_output/prod_singlefile.py --fake
  cd python && python src/base_practice/20_prod_structured_output/prod_pure.py --dry-run
"""
