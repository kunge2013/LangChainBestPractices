from langchain.agents import create_agent
from langchain_core.tools import tool
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
import os

model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
)

email_sys_prompt = (
    "You are an email assistant."
    "WORKFLOW (MUST FOLLOW THIS EXACT ORDER):"
    "STEP 1: Parse the user's request to extract recipient, subject, and body"
    "STEP 2: use send_email to send msg"
    "STEP 3: ALWAYS confirm what was sent in your final response"
)


@tool
def send_email(
        to: list[str], # email addresses
        subject: str,  # ISO format: "2025-01-02"
        body: str,
        cc: list[str] = []
) -> list[str]:
    """send an email via email API . Requires properly formatted addresses"""
    # Stub: in practice , this would call sendgrid gmail api
    return f"email send to {','.join(to) } - Subject = {subject}, cc={','.join(cc)}"



email_agent = create_agent(
    model=model,
    system_prompt=email_sys_prompt,
    tools=[ send_email]
)


def test_agent():
    for event in email_agent.stream(
            {"messages": [
                {
                    "role": "user", "content": "发送邮件给54388@qq.com, 内容：你好，标题:测试, 抄送:998@qq.com"
                }
            ]}, stream_mode="values"
    ):
        event["messages"][-1].pretty_print()
