# Task 1 Brief: Dependencies & Configuration

**Context:** This is Task 1 of 7 in the deep-agent-ide integration. The project is a Vue 3 + LangGraph application with patterns-based architecture. Each pattern is a self-contained agent with its own UI. We're adding a second pattern (deep-agent-ide) that provides an IDE-style interface with file tree, code editor, diff viewer, and chat panel.

**Goal:** Add the hono and langsmith dependencies, register the IDE agent graph in langgraph.json, add the sandbox proxy in vite.config.ts, and register the IDE slug in agent-config.ts.

## Global Constraints

- Package manager: pnpm
- Node version: 22
- Path alias: `@/*` maps to `src/*`
- Port: Vite 4100, LangGraph 2024
- DRY, YAGNI, frequent commits

## Steps

### Step 1: Add dependencies to package.json

Add `hono` and `langsmith` to the `dependencies` section:
```json
"hono": "^4.12.26",
"langsmith": "^0.7.5"
```

### Step 2: Update langgraph.json

Replace entire file content:
```json
{
  "node_version": "22",
  "graphs": {
    "deep_agent_subagent_cards": "./src/agents/deep-agent-subagent-cards.ts:agent",
    "deep_agent_ide": "./src/agents/deep-agent-ide.ts:agent"
  },
  "http": {
    "app": "./src/api/app.ts:app"
  },
  "env": ".env"
}
```

### Step 3: Add sandbox proxy to vite.config.ts

Add `"/sandbox"` to the proxy object. Keep existing proxies unchanged.

### Step 4: Register IDE slug in agent-config.ts

Add `"deep-agent-ide": "deep_agent_ide"` to SLUG_TO_ASSISTANT.

### Step 5: Run pnpm install

Run `pnpm install`. Verify hono and langsmith installed successfully.

### Step 6: Commit

```bash
git add package.json langgraph.json vite.config.ts src/agent-config.ts pnpm-lock.yaml
git commit -m "feat: add deep-agent-ide config and dependencies"
```

## Report

Write to: `.superpowers/sdd/task-1-report.md`
Return: status, commits, test summary, concerns
