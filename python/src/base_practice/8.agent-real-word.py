### 更复杂一点的智能体 create_agent
## 大模型:model
##系统提示词:system_prompt-new
##工具:tools，用户消息传递参数
# =>工具运行时上下文传递参数:contextschema-new
## 记忆管理:checkpointer

##结构化输出:response_format - new

# agent tools 调用
from langchain.agents import create_agent
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
import os
from dataclasses import dataclass

load_dotenv()

model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
    # qwen3.5-plus 默认开启 thinking 模式，该模式下不支持 tool_choice="required"/"any"
    # 而 create_agent 使用 response_format 时会设置 tool_choice="any" 来强制工具调用，
    # 因此需要关闭 thinking 模式
    extra_body={"enable_thinking": False},
)

SYSTEM_PROMPT = """You are an expert weather forecaster, who speaks in puns.
    You have access to two tools:
    get_weather_for_location: use this to get the weather for a specific location
    get_user_location: use this to get the user's location
    If a user asks you for the weather, make sure you know the location. If you can tell from question that they are , use get_user_location tools
用中文回答
"""


# 天气
@tool
def ge_weather_for_location(city: str):
    """get weather for location city . """
    return f"its always sunny in {city}!"


# 工具运行时上下文参数
@dataclass
class Context:
    """Custom runtime context schema ."""
    user_id: str


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user information based on user ID. """
    user_id = runtime.context.user_id
    return "FLO" if user_id == "1" else "SF"


# 结构化输出
@dataclass
class ResponseFormat:
    """RESPONSE schema for the agent . """
    # A punny_response (always required)
    punny_response: str
    # Any interesting information about the weather if available
    weather_conditions: str | None = None


# 记忆管理
checkpointer = InMemorySaver()

# 配置
config = {"configurable": {"thread_id": "1"}}
# 创建智能体
agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_user_location, ge_weather_for_location],
    context_schema=Context,
    response_format=ResponseFormat,
    checkpointer=checkpointer,
)

# 对话
response = agent.invoke(
    {"messages": [{"role": "user", "content": "what is weather outside"}]},
    config=config,
    context=Context(user_id="1"))

print(response['structured_response'])

# 第二轮
response = agent.invoke(
    {"messages": [{"role": "user", "content": "thank u"}]},
    config=config,
    context=Context(user_id="1"))

print(response['structured_response'])