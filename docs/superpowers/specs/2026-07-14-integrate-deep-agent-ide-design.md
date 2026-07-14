# Design Spec: Integrate Deep Agent IDE

**Date**: 2026-07-14
**Status**: Draft

## Overview

Integrate the `deep-agent-ide` source code (a three-column IDE layout with file tree, code editor, diff viewer, and chat panel) into the existing TypeScript LangChain project. The IDE becomes a second agent pattern alongside the existing subagent-cards pattern, accessible via a top navigation menu.

**Key decisions**:
- Sandbox: LocalShellBackend (local temp directories, development only)
- Architecture: Flatten everything into the existing project
- Model: OpenAI-compatible (`openai:${OPENAI_MODEL}`, defaults to `qwen3.5-plus`)

## Architecture

### File Structure

```
typescript/src/
├── agents/
│   ├── deep-agent-subagent-cards.ts   # existing
│   └── deep-agent-ide.ts              # new
├── api/
│   ├── app.ts                         # new: Hono app
│   ├── sandbox.ts                     # new: REST routes
│   ├── sandbox-security.ts            # new: security utils
│   └── utils.ts                       # new: sandbox management
├── patterns/
│   ├── deep-agent-subagent-cards/     # existing
│   └── deep-agent-ide/                # new (10 files)
│       ├── Preview.vue
│       ├── ChatPanel.vue
│       ├── CodePanel.vue
│       ├── FileTree.vue
│       ├── FileTreeItem.vue
│       ├── FileIcon.vue
│       ├── file-icon.ts
│       ├── ChangedFilesSummary.vue
│       ├── types.ts
│       └── use-sandbox-files.ts
├── components/                        # unchanged
└── shared-styles/                     # unchanged
```

### Navigation

Top-level tab bar in `App.vue` with clickable buttons for each pattern. `activePattern` ref controls which `Preview.vue` renders. The `main` container uses `min-h-0` for proper flex layout with `overflow-hidden` children.

Pattern registry in `agent-config.ts`:
```typescript
const SLUG_TO_ASSISTANT: Record<string, string> = {
  "deep-agent-subagent-cards": "deep_agent_subagent_cards",
  "deep-agent-ide": "deep_agent_ide",
};
```

## Components

### Agent Definition

`src/agents/deep-agent-ide.ts`:
- `createDeepAgent` from `deepagents` library
- Model: `openai:${process.env.OPENAI_MODEL || "qwen3.5-plus"}`
- Backend: `getOrCreateSandboxForThread(threadId)` returning `LocalShellBackend`
- System prompt: Expert Node.js developer on `/app` todo-api project
- Recursion limit: 200
- Exports: `agent(runtime: LangGraphRunnableConfig)`

### Sandbox API

**Hono app** (`src/api/app.ts`):
```typescript
import { Hono } from "hono";
import { registerSandbox } from "./sandbox.js";

export const app = new Hono();
registerSandbox(app);
```

**Routes** (`src/api/sandbox.ts`):
| Route | Purpose |
|-------|---------|
| `GET /sandbox/:threadId/tree` | Full file tree (glob `**`) |
| `GET /sandbox/:threadId/file` | Single file content |
| `GET /sandbox/:threadId/ls` | Directory listing |
| `GET /sandbox/:threadId/info` | Sandbox status (running/stopped) |

**Security**:
- Path validation: `^/app(/[\w.-])*$` regex + manual `..` resolution
- Thread ID validation: `^[a-zA-Z0-9_-]{1,128}$`
- `hardenSandbox`: minimal wrapper (pass-through since LocalShellBackend is already isolated)
- Security instructions injected into agent system prompt

**Sandbox seeding**: Each thread's sandbox is seeded with a sample todo-api project:
- `package.json`, `README.md`
- `src/index.js` (HTTP server), `src/store.js` (TodoStore), `src/router.js` (REST handlers)
- `npm install` runs after seeding

### Frontend Components

**Preview.vue** - Three-column IDE layout:
- Left (160px): FileTree + ChangedFilesSummary
- Center (flex-1): CodePanel (code view + diff view)
- Right (256px): ChatPanel (messages + input)

**CodePanel.vue** - Code/diff viewer:
- Shiki syntax highlighting with line numbers
- Diff view via `@git-diff-view/vue` (unified diff)
- Tab switcher between Code and Diff (Diff tab appears only for changed files)

**ChatPanel.vue** - Chat interface:
- Human/AI message bubbles
- Compact tool summaries (`read_file`, `ls`, `glob`, `grep`)
- Pending tool call display
- Error display, loading indicator, preset prompts

**FileTree.vue** + **FileTreeItem.vue** - Sidebar file tree:
- Expand/collapse folders
- VS Code-style file icons from `@iconify-json/vscode-icons`
- Changed file indicator (amber dot)
- Click to select file

**useSandboxFiles.ts** - Composable for file operations:
- File tree fetching and caching
- File content caching
- Diff calculation (current vs original snapshot)
- Changed file tracking
- Thread-bound sandbox connection

## Data Flow

```
User selects "IDE" tab
  → DeepAgentIdePreview renders
  → useStream connects to /api/langgraph (Vite proxy → port 2024)
  → Agent creates LocalShellBackend for thread (temp dir)
  → Sandbox seeded with todo-api + npm install
  → useSandboxFiles fetches file tree via /sandbox/:threadId/tree
  → User sends prompt
  → Agent modifies files via shell tools
  → File mutating tool calls trigger refreshSingleFile/refreshTreeAndFiles
  → UI updates: file tree, code view, diff, changed files summary
```

## Build Configuration

### langgraph.json
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

### vite.config.ts proxy additions
```typescript
proxy: {
  "/sandbox": {
    target: "http://127.0.0.1:2024",
    changeOrigin: true,
  },
}
```
Existing `/api/langgraph` and `/threads` proxies remain unchanged.

### package.json additions
- `hono`: ^4.12.26
- `langsmith`: ^0.7.5

### Vite dev workflow
No change to scripts:
- `pnpm run dev` → starts both agent server (port 2024) + frontend (port 4100)
- Sandbox routes served on same port 2024 via Hono HTTP app
- All proxied through Vite for same-origin communication

## Error Handling

- Agent errors: displayed in ChatPanel with retry option
- Sandbox errors: JSON error responses from Hono routes (400 for invalid paths, 500 for execution failures)
- File not found: 404 from sandbox routes
- Network errors: handled by `useStream` error state
- Missing thread: auto-created on component mount

## Testing

- Verify both agents start with `pnpm run dev`
- Test navigation between Subagent Cards and IDE patterns
- Test IDE chat: send prompt, verify agent responds
- Test sandbox: verify file tree shows seeded project
- Test file editing: agent modifies files, UI updates
- Test diff view: shows unified diff for changed files
- Production build: `pnpm run build` succeeds
