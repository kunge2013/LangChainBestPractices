# deep-agent-ide — LangChain Pattern

This is a standalone **Vue** + **TypeScript** project for the **deep-agent-ide** LangChain UI pattern.

## Sandbox backend

This pattern requires `LANGSMITH_API_KEY` for LangSmith sandboxes. **Deployed LangGraph agents typically inject this automatically.** Add it to `packages/agent/.env` for local runs.


## Prerequisites

- Node.js 22+
- [pnpm](https://pnpm.io/) (`npm install -g pnpm`)
- An [Anthropic API key](https://console.anthropic.com/)
- A [LangSmith API key](https://smith.langchain.com/settings) (required for sandboxes)

## Setup

1. Copy the environment file and add your API key:
   ```bash
   cp .env.example packages/agent/.env
   # Edit packages/agent/.env — set ANTHROPIC_API_KEY and LANGSMITH_API_KEY
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

## Running

```bash
pnpm run dev
```

This starts both the LangGraph agent server (port 2024) and the Vite frontend (port 4100).

The Vite dev server proxies `/api/langgraph` to `http://127.0.0.1:2024`, and the app uses that same-origin URL for the LangGraph SDK (no browser CORS issues in local dev).

Open [http://localhost:4100](http://localhost:4100) in your browser.
