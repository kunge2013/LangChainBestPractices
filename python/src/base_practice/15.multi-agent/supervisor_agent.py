### 说明

## agent: model, tools, system_prompt, checkerpoint, middleware

### 多   agent lanchain1.0 推两种方式
# 1.supervisor agent  集中式
#     user=> supervisor agent => worker agents

# 2.handoff agent , 轮换式
# user=>  agent1 ===> user=> agent2

# 整个四关于supervisor 集中式

### 步骤：
# 1.创建2个 woker agent ,有各自的tools
# 2.把2个woker agent 封装成2个新的tool
# 3.创建 supervisor 智能体， 配置 tools ， 把封装的tool 个agent 使用


### 内容
# 1.supervisor agent:个人助理
# 2.个worker agent : calendar_agent, email_agent

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from calendar_agent import calendar_agent
from email_agent import email_agent

load_dotenv()
import os

model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
)

supervisor_prompt = (
    "You are a helpful personal assistant."
    "You can schedule calendar events and send emails."
    "Break down user requests into appropriate tool calls and coordinate the results."
    "When a request involves multiple actions, use multiple tools in sequence."
)

@tool
def schedule_event(request:str) -> str:
    """Schedule calendar events using natural language.

    Use this when the user wants to create, modify, or check calendar appointments.
    Handles date/time parsing, availability checking, and event creation.

    Input: Natural language scheduling request
    (e.g., 'meeting with design teamnext Tuesday at 2pm')"""
    result = calendar_agent.invoke(
        {"messages": [
            {
                "role": "user", "content": request
            }
        ]}
    )
    return result["messages"][-1].text


@tool
def manage_email(request:str) -> str:
    """ Send emails using natural language.

    Use this when the user wants to send notifications, reminders, or any email communication.
    Handles recipient extraction, subject generation, and email composition.

    Input: Natural language email request (e.g., 'send them a reminder about the meeting')"""
    result = email_agent.invoke(
        {"messages": [
            {
                "role": "user", "content": request
            }
        ]}
    )
    return result["messages"][-1].text



supervisor_agent = create_agent(
    model=model,
    system_prompt=supervisor_prompt,
    tools=[schedule_event, manage_email]
)


def test_supervisor_agent():
    for event in supervisor_agent.stream(
            {"messages": [
                {
                    "role": "user", "content": "定时提醒我， 2026-01-01 8点 会议， 发邮件通知给7667@qq.com ，抄送 676@qq.com"
                }
            ]}, stream_mode="values"
    ):
        event["messages"][-1].pretty_print()

test_supervisor_agent()