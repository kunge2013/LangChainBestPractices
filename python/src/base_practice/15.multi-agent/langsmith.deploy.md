# 1.架构说明
langsmith: logging tool

smith.langchain.com 注册账户，申请api key
程序里边使用.env，定义环境变量
studio: 部署agent

agent chat-ui: 和部署agent交互
# 2.环境配置
.env
DEEPSEEK_API_KEY="sk-..."

LANGSMITH_TRACING="true"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="..."
LANGSMITH_PROJECT="my-multi-agent"

