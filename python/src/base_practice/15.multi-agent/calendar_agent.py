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

calendar_prompt = (
    "You are a calendar scheduling assistant."
    "IMPORTANT RULES:"
    "1. ALWAYS call get_available_time_slots FIRST before creating any event"
    "2. Only call create_calendar_event AFTER verifying availability"
    "3. Parse natural language scheduling requests into proper ISO datetime formats"
    "4. If any slot is unavailable, suggest alternative times from get_available_time_slots"
    "5. Always confirm what was scheduled in your final response"
)


@tool
def get_available_time_slots(
        attendees: list[str],
        date: str,  # ISO format: "2025-01-02"
        duration_minutes: int
) -> list[str]:
    """Check calendar availability for given attendees on a specific date """
    # Stub: in practice , this would query calendar APIS
    return ["9:00", "14:00", "16:00"]


@tool
def create_calendar_event(
        title: str,
        start_time: str,  # ISO format: "2025-01-02 00:00:00"
        end_time: str,  # ISO format: "2025-01-02 00:00:00"
        attendees: list[str],  # email addresss
        location: str = ""
) -> list[str]:
    """'Create a calendar event, Requires exact Iso datetime format. """
    # Stub: In practice, this would call Google calendar API, Outlook
    return f"Event created:{title} from {start_time} to {end_time} with  {len(attendees)} attendees , in {location}"


calendar_agent = create_agent(
    model=model,
    system_prompt=calendar_prompt,
    tools=[ get_available_time_slots, create_calendar_event]
)


def test_cac_agent():
    for event in calendar_agent.stream(
            {"messages": [
                {
                    "role": "user", "content": "Schedule meeting ['design-team@qq.com'] on 2026-08-01 at 2pm 1 hour"
                }
            ]}, stream_mode="values"
    ):
        event["messages"][-1].pretty_print()
