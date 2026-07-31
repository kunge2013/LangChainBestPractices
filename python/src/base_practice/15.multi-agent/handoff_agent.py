# handoff_agent.py
"""
Handoff Agent 轮换式多智能体系统

工作流程：
1. 用户请求进入主agent
2. 主agent根据请求类型，将任务handoff给专门的子agent
3. 子agent完成任务后，将控制权handoff回主agent或直接返回结果
4. 支持链式handoff：主agent -> email agent -> calendar agent
"""

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal, List, Optional
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime

load_dotenv()
import os

# ============ 配置模型 ============
model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
)

# ============ 定义状态 ============
class AgentState(TypedDict):
    messages: List[dict]
    next_agent: str
    original_request: str
    current_agent: str
    history: List[str]
    final_result: Optional[str]

# ============ 定义工具函数 ============
@tool
def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============ 定义Email Agent ============
email_handoff_prompt = (
    "You are an Email Agent specializing in email operations.\n"
    "WORKFLOW (MUST FOLLOW THIS EXACT ORDER):\n"
    "STEP 1: Parse the user's request to extract: recipient(s), subject, body, and cc\n"
    "STEP 2: Call send_email tool to send the email\n"
    "STEP 3: Confirm what was sent in your final response\n"
    "IMPORTANT: After completing the email task, you MUST call handoff_back_to_main agent to return control."
)

@tool
def send_email(
        to: List[str],
        subject: str,
        body: str,
        cc: List[str] = []
) -> str:
    """发送邮件。需要正确格式的邮件地址"""
    # 模拟邮件发送
    cc_text = f", CC: {', '.join(cc)}" if cc else ""
    return f"✅ 邮件已发送至 {', '.join(to)}，主题: {subject}{cc_text}"

@tool
def handoff_back_to_main(
        result: str
) -> str:
    """将控制权交还给主Agent。任务完成后必须调用此工具。"""
    return f"HANDOFF: return to main agent with result: {result}"

email_agent = create_agent(
    model=model,
    system_prompt=email_handoff_prompt,
    tools=[send_email, handoff_back_to_main]
)

# ============ 定义Calendar Agent ============
calendar_handoff_prompt = (
    "You are a Calendar Agent specializing in scheduling and calendar management.\n"
    "IMPORTANT RULES:\n"
    "1. ALWAYS call get_available_time_slots FIRST before creating any event\n"
    "2. Only call create_calendar_event AFTER verifying availability\n"
    "3. Parse natural language scheduling requests into proper ISO datetime formats\n"
    "4. If any slot is unavailable, suggest alternative times\n"
    "5. After completing the scheduling task, call handoff_back_to_main to return control"
)

@tool
def get_available_time_slots(
        attendees: List[str],
        date: str,
        duration_minutes: int
) -> List[str]:
    """检查特定日期的可用时间段"""
    # 模拟可用时间段
    return ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]

@tool
def create_calendar_event(
        title: str,
        start_time: str,
        end_time: str,
        attendees: List[str],
        location: str = ""
) -> str:
    """创建日历事件。需要精确的ISO日期时间格式。"""
    # 模拟创建事件
    location_text = f" @ {location}" if location else ""
    return f"✅ 已创建事件: {title}{location_text}\n时间: {start_time} 至 {end_time}\n参与者: {', '.join(attendees)}"

@tool
def handoff_back_to_main_calendar(
        result: str
) -> str:
    """将控制权交还给主Agent。任务完成后必须调用此工具。"""
    return f"HANDOFF: return to main agent with result: {result}"

calendar_agent = create_agent(
    model=model,
    system_prompt=calendar_handoff_prompt,
    tools=[get_available_time_slots, create_calendar_event, handoff_back_to_main_calendar]
)

# ============ 定义主Agent (Handoff Controller) ============
main_agent_prompt = (
    "You are the Main Personal Assistant Agent that coordinates tasks.\n"
    "You can handoff tasks to specialized agents:\n"
    "- Use 'handoff_to_email_agent' for email-related tasks (sending, composing emails)\n"
    "- Use 'handoff_to_calendar_agent' for scheduling and calendar tasks\n"
    "RULES:\n"
    "1. Analyze the user request and decide which agent should handle it\n"
    "2. For single tasks, handoff once and receive the result\n"
    "3. For complex requests, you can chain multiple handoffs\n"
    "4. After receiving results from other agents, compile and present the final answer\n"
    "5. If a task requires multiple steps (e.g., schedule meeting AND send email), do them in sequence"
)

@tool
def handoff_to_email_agent(request: str) -> str:
    """将邮件任务移交给Email Agent处理。

    适用场景：发送邮件、撰写邮件、回复邮件等。
    输入：用自然语言描述的邮件任务。
    """
    result = email_agent.invoke(
        {"messages": [{"role": "user", "content": request}]}
    )
    return result["messages"][-1].content

@tool
def handoff_to_calendar_agent(request: str) -> str:
    """将日历任务移交给Calendar Agent处理。

    适用场景：创建会议、安排日程、检查可用时间等。
    输入：用自然语言描述的日程任务。
    """
    result = calendar_agent.invoke(
        {"messages": [{"role": "user", "content": request}]}
    )
    return result["messages"][-1].content

# 创建主Agent
main_agent = create_agent(
    model=model,
    system_prompt=main_agent_prompt,
    tools=[handoff_to_email_agent, handoff_to_calendar_agent]
)

# ============ 使用LangGraph实现更复杂的Handoff流程 ============
def create_handoff_graph():
    """使用LangGraph实现更复杂的handoff流程控制"""

    # 定义节点
    def main_agent_node(state: AgentState):
        """主Agent节点 - 接收用户请求并决定handoff给谁"""
        messages = state["messages"]
        response = main_agent.invoke({"messages": messages})
        last_message = response["messages"][-1]

        # 检查是否调用了handoff工具
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            tool_name = last_message.tool_calls[0]["name"]
            state["next_agent"] = tool_name
        else:
            state["next_agent"] = "end"
            state["final_result"] = last_message.content

        state["messages"] = response["messages"]
        return state

    def email_agent_node(state: AgentState):
        """Email Agent节点"""
        messages = state["messages"]
        response = email_agent.invoke({"messages": messages})
        state["messages"] = response["messages"]
        state["next_agent"] = "main"
        return state

    def calendar_agent_node(state: AgentState):
        """Calendar Agent节点"""
        messages = state["messages"]
        response = calendar_agent.invoke({"messages": messages})
        state["messages"] = response["messages"]
        state["next_agent"] = "main"
        return state

    # 构建图
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("main", main_agent_node)
    graph.add_node("email_agent", email_agent_node)
    graph.add_node("calendar_agent", calendar_agent_node)

    # 定义路由
    def router(state: AgentState) -> Literal["email_agent", "calendar_agent", "end"]:
        if state["next_agent"] == "handoff_to_email_agent":
            return "email_agent"
        elif state["next_agent"] == "handoff_to_calendar_agent":
            return "calendar_agent"
        else:
            return "end"

    # 添加边
    graph.set_entry_point("main")
    graph.add_conditional_edges("main", router, {
        "email_agent": "email_agent",
        "calendar_agent": "calendar_agent",
        "end": END
    })
    graph.add_edge("email_agent", "main")
    graph.add_edge("calendar_agent", "main")

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

# ============ 测试函数 ============

def test_handoff_email():
    """测试单独的邮件任务 - Handoff模式"""
    print("=" * 60)
    print("测试1: Handoff到Email Agent (发送邮件)")
    print("=" * 60)

    for event in main_agent.stream(
            {"messages": [{
                "role": "user",
                "content": "请帮我发送一封邮件给张三@qq.com，主题是'会议提醒'，内容是'明天下午3点有项目会议，请准时参加'，抄送给李四@qq.com"
            }]},
            stream_mode="values"
    ):
        if event.get("messages"):
            event["messages"][-1].pretty_print()
            print()

def test_handoff_calendar():
    """测试单独的日历任务 - Handoff模式"""
    print("=" * 60)
    print("测试2: Handoff到Calendar Agent (安排会议)")
    print("=" * 60)

    for event in main_agent.stream(
            {"messages": [{
                "role": "user",
                "content": "帮我安排一个会议，明天下午2点，1小时，参与者有：design-team@qq.com, product-team@qq.com，会议标题是'产品设计评审'，地点在会议室A"
            }]},
            stream_mode="values"
    ):
        if event.get("messages"):
            event["messages"][-1].pretty_print()
            print()

def test_handoff_chain():
    """测试链式Handoff - 先日历再邮件"""
    print("=" * 60)
    print("测试3: 链式Handoff (先安排会议，再发送通知邮件)")
    print("=" * 60)

    # 使用主Agent进行链式处理
    for event in main_agent.stream(
            {"messages": [{
                "role": "user",
                "content": "帮我完成以下任务：1) 安排明天下午3点的团队会议，1小时，参与者有team@qq.com 2) 会议安排好后，发送邮件通知给所有参与者"
            }]},
            stream_mode="values"
    ):
        if event.get("messages"):
            event["messages"][-1].pretty_print()
            print()

def test_complex_request():
    """测试复杂请求 - 多个handoff"""
    print("=" * 60)
    print("测试4: 复杂请求 - 包含多个任务")
    print("=" * 60)

    for event in main_agent.stream(
            {"messages": [{
                "role": "user",
                "content": "首先发送一封邮件给经理@qq.com，汇报本周工作进展，然后在下周一上午10点安排一个1小时的团队会议"
            }]},
            stream_mode="values"
    ):
        if event.get("messages"):
            event["messages"][-1].pretty_print()
            print()

def test_graph_handoff():
    """使用LangGraph测试Handoff流程"""
    print("=" * 60)
    print("测试5: LangGraph Handoff流程")
    print("=" * 60)

    graph = create_handoff_graph()
    config = {"configurable": {"thread_id": "1"}}

    initial_state = {
        "messages": [{"role": "user", "content": "请帮我发送邮件给test@qq.com，通知他们明天下午3点的会议"}],
        "next_agent": "main",
        "original_request": "",
        "current_agent": "",
        "history": [],
        "final_result": None
    }

    for event in graph.stream(initial_state, config, stream_mode="values"):
        if event.get("messages"):
            print(f"Agent: {event.get('current_agent', 'unknown')}")
            event["messages"][-1].pretty_print()
            print("-" * 40)

# ============ 运行测试 ============
test_handoff_chain()
