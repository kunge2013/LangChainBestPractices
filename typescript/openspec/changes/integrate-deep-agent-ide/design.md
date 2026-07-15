# Design: Integrate Deep Agent IDE

## Context

The existing project at `typescript/` is a Vue 3 + Vite + LangGraph application with:
- A single agent (`deep-agent-subagent-cards`) using `createDeepAgent` with OpenAI-compatible models
- Chat-based UI with subagent cards
- `pnpm` package manager, Vite dev server on port 4100, LangGraph agent server on port 2024

The `deep-agent-ide` source code is a pnpm monorepo with:
- Agent: `packages/agent/` - uses `createDeepAgent` with `anthropic:claude-haiku-4-5` model, includes sandbox API routes (Hono)
- Frontend: `packages/frontend/` - three-column IDE layout (file tree, code panel, chat panel)

## Architecture

### Directory Structure After Integration

```
typescript/
├── src/
│   ├── main.ts                          # (modified) unchanged - still mounts App.vue
│   ├── App.vue                          # (modified) adds top menu navigation
│   ├── constants.ts                     # (unchanged)
│   ├── agent-config.ts                  # (modified) adds deep-agent-ide slug
│   ├── styles.css                       # (unchanged)
│   ├── shared-styles/
│   │   ├── tokens.css                   # (unchanged)
│   │   └── base.css                     # (unchanged)
│   ├── agents/
│   │   ├── deep-agent-subagent-cards.ts # (unchanged)
│   │   └── deep-agent-ide.ts            # (new) IDE agent definition
│   ├── api/
│   │   ├── sandbox.ts                   # (new) sandbox REST endpoints
│   │   ├── sandbox-security.ts          # (new) security utilities
│   │   └── utils.ts                     # (new) sandbox management, seed data
│   ├── components/
│   │   ├── playground.ts                # (modified) adds IDE-specific component exports
│   │   ├── Markdown.vue                 # (unchanged)
│   │   ├── PatternListView.vue          # (unchanged)
│   │   ├── cards/                       # (unchanged)
│   │   └── chat/                        # (unchanged)
│   └── patterns/
│       ├── deep-agent-subagent-cards/   # (unchanged)
│       │   ├── Preview.vue
│       │   └── types.ts
│       └── deep-agent-ide/              # (new) IDE pattern
│           ├── Preview.vue              # Main orchestrator (3-column layout)
│           ├── ChatPanel.vue
│           ├── CodePanel.vue
│           ├── FileTree.vue
│           ├── FileTreeItem.vue
│           ├── FileIcon.vue
│           ├── file-icon.ts
│           ├── ChangedFilesSummary.vue
│           ├── types.ts
│           └── use-sandbox-files.ts
├── langgraph.json                       # (modified) adds deep_agent_ide graph
├── vite.config.ts                       # (modified) adds sandbox API proxy
└── package.json                         # (modified) may add @langchain/anthropic dependency
```

### Key Decisions

#### 1. Model Configuration

The IDE agent currently uses `anthropic:claude-haiku-4-5`. We'll switch to the project's existing OpenAI-compatible model:

```typescript
const modelEnv = process.env.OPENAI_MODEL || "qwen3.5-plus";
const model = `openai:${modelEnv}`;
```

This matches the existing `deep-agent-subagent-cards` agent pattern.

#### 2. Navigation

Add a simple top navigation bar in `App.vue` with clickable tabs:
- "Subagent Cards" (current)
- "IDE" (new)

State is managed via a `ref` in `App.vue`. The selected pattern renders its `Preview.vue`.

#### 3. Sandbox API Integration

The IDE pattern requires sandbox API endpoints (`/sandbox/:threadId/*`). These are served by the Hono app in the original monorepo's `packages/agent/`. Since our project already runs a LangGraph dev server via `langgraphjs dev`, we need to:

- **Option A (recommended)**: Flatten the sandbox API into the existing agent structure. The sandbox routes (`sandbox.ts`, `utils.ts`, `sandbox-security.ts`) are served alongside the agent via the LangGraph server's HTTP app configuration in `langgraph.json`. Add `"http": { "app": "./src/api/app.ts:app" }` to `langgraph.json`.
- **Option B**: Keep sandbox logic separate and proxy through Vite.

We'll use Option A: register a Hono app via `langgraph.json`'s `http.app` config that serves the sandbox endpoints, alongside the agent graph.

#### 4. Agent Registration

The new agent is registered in `langgraph.json`:
```json
{
  "graphs": {
    "deep_agent_subagent_cards": "./src/agents/deep-agent-subagent-cards.ts:agent",
    "deep_agent_ide": "./src/agents/deep-agent-ide.ts:agent"
  },
  "http": {
    "app": "./src/api/app.ts:app"
  }
}
```

#### 5. Pattern Slug Registration

`agent-config.ts` gets a new entry:
```typescript
const SLUG_TO_ASSISTANT: Record<string, string> = {
  "deep-agent-subagent-cards": "deep_agent_subagent_cards",
  "deep-agent-ide": "deep_agent_ide",
};
```

## Data Flow

```
User selects "IDE" tab in App.vue
    |
    v
DeepAgentIdePreview.vue renders
    |
    v
useStream connects to LangGraph server at /api/langgraph
    |
    v
Agent (deep-agent-ide.ts) creates DeepAgent with OpenAI model + sandbox backend
    |
    v
Sandbox routes (/sandbox/:threadId/*) handle file operations
    |
    v
useSandboxFiles composable fetches file tree, content, diffs
    |
    v
Preview.vue renders 3-column layout: FileTree | CodePanel | ChatPanel
```

## Security Notes

- The sandbox seeding creates a sample project in an isolated environment
- `hardenSandbox()` wraps the sandbox (note: `hardened-sandbox.ts` is missing in the source and will need to be created or simplified)
- Sandbox backend uses `LocalShellBackend` in development (local temp directory)
- Path validation via regex: `^/app(/[\w.-])*$`
