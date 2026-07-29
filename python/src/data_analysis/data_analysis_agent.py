# [AGC:FILE] tool=Cc author=fangkun date=2026-07-29
from dotenv import load_dotenv
load_dotenv()

import csv
import io
import os

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.utils.uuid import uuid7

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

# ---------------------------------------------------------------------------
# Backend setup
# ---------------------------------------------------------------------------
backend = LocalShellBackend(
    root_dir=".",
    virtual_mode=True,
    env={"PATH": "/usr/bin:/bin"},
)

# ---------------------------------------------------------------------------
# Sample data creation & upload
# ---------------------------------------------------------------------------
data = [
    ["Date", "Product", "Units Sold", "Revenue"],
    ["2025-08-01", "Widget A", 10, 250],
    ["2025-08-02", "Widget B", 5, 125],
    ["2025-08-03", "Widget A", 7, 175],
    ["2025-08-04", "Widget C", 3, 90],
    ["2025-08-05", "Widget B", 8, 200],
]

text_buf = io.StringIO()
writer = csv.writer(text_buf)
writer.writerows(data)
csv_bytes = text_buf.getvalue().encode("utf-8")
text_buf.close()

backend.upload_files([("/root/data/sales_data.csv", csv_bytes)])

# ---------------------------------------------------------------------------
# Custom tools
# ---------------------------------------------------------------------------
tools = []

# Slack tool (optional — only added if token is configured)
slack_token = os.environ.get("SLACK_USER_TOKEN")
if slack_token:
    from slack_sdk import WebClient

    slack_client = WebClient(token=slack_token)
    slack_channel = os.environ.get("SLACK_CHANNEL", "C0123456ABC")

    @tool(parse_docstring=True)
    def slack_send_message(text: str, file_path: str | None = None) -> str:
        """Send message, optionally including attachments such as images.

        Args:
            text: (str) text content of the message
            file_path: (str) file path of attachment in the filesystem.
        """
        if not file_path:
            slack_client.chat_postMessage(channel=slack_channel, text=text)
        else:
            fp = backend.download_files([file_path])
            slack_client.files_upload_v2(
                channel=slack_channel,
                content=fp[0].content,
                initial_comment=text,
            )
        return "Message sent."

    tools.append(slack_send_message)

# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------
model = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "qwen3.5-plus"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2000")),
)

checkpointer = InMemorySaver()

agent = create_deep_agent(
    model=model,
    tools=tools,
    backend=backend,
    checkpointer=checkpointer,
)

thread_id = str(uuid7())
config = {"configurable": {"thread_id": thread_id}}

# ---------------------------------------------------------------------------
# Run the agent
# ---------------------------------------------------------------------------
input_message = {
    "role": "user",
    "content": (
        "Analyze /root/data/sales_data.csv and generate a beautiful plot. "
        "When finished, save the analysis report and plot locally."
    ),
}

stream = agent.stream_events(
    {"messages": [input_message]},
    config,
    version="v3",
)
for snapshot in stream.values:
    snapshot["messages"][-1].pretty_print()

# ---------------------------------------------------------------------------
# Download artifacts
# ---------------------------------------------------------------------------
print("\n--- Downloading artifacts ---")
try:
    result = backend.download_files(["/root/sales_analysis_plot.png"])
    print(f"Downloaded: {result}")
except Exception as e:
    print(f"Could not download artifact (may not have been generated): {e}")
# [AGC:END]
