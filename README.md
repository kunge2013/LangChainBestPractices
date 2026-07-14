# LangChainBestPractices

langchain 最佳实践

## Prerequisites

- Node.js 22+
- [pnpm](https://pnpm.io/) (`npm install -g pnpm`)

## Setup

1. Copy the environment file and add your API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
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
