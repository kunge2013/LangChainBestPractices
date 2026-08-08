# [AGC:FILE] tool=Cc author=fangkun date=2026-08-08
"""
billing_manual_langgraph
========================
LangGraph API entry point for the billing_manual package.

This module exposes a module-level `agent` variable that LangGraph
discovers via langgraph.json configuration.

Usage:
    langgraph dev

The agent is built at import time (same pattern as other LangGraph entry
points in this project). For more control, import directly from
`billing_manual` and call `build_agent()` explicitly.
"""

from billing_manual import build_agent

# [AGC:START] tool=Cc author=fangkun

# Module-level agent variable for LangGraph to discover
agent = build_agent()

# [AGC:END]
