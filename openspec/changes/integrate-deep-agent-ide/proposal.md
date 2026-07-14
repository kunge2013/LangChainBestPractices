# Proposal: Integrate Deep Agent IDE

## Problem

The project currently has a single agent pattern (subagent-cards) rendered directly in `App.vue`. The `deep-agent-ide` source code exists as a separate standalone monorepo with a full IDE-style interface (file tree, code editor, diff viewer, and chat panel). We want to integrate it as an additional agent pattern within the existing project, using a main menu to navigate between different agents.

## Solution

Integrate the `deep-agent-ide` frontend components and agent definition into the existing TypeScript project structure. Add a top-level navigation menu in `App.vue` to switch between the existing subagent-cards pattern and the new IDE pattern. Convert the IDE agent's model from Anthropic to OpenAI (using the existing OpenAI-compatible configuration).

## Scope

### In scope
- Copy IDE frontend components (`FileTree`, `FileTreeItem`, `FileIcon`, `CodePanel`, `ChatPanel`, `ChangedFilesSummary`, `use-sandbox-files` composable, types) into `src/patterns/deep-agent-ide/`
- Copy the sandbox API routes (`sandbox.ts`, `utils.ts`, `sandbox-security.ts`) into the agent side
- Add the `deep-agent-ide` agent definition using OpenAI model (matching existing `qwen3.5-plus` configuration)
- Update `langgraph.json` to register the new agent graph
- Update `agent-config.ts` to register the IDE pattern slug
- Add a main menu/navigation to `App.vue` for switching between agents
- Add the sandbox API proxy to `vite.config.ts`

### Out of scope
- Creating additional agent patterns beyond the two already planned
- Replacing Anthropic models in production (we'll use the existing OpenAI-compatible endpoint)
- Modifying the existing subagent-cards pattern

## Impact

- `src/App.vue` -- gains navigation/menu logic
- `src/agent-config.ts` -- new slug registration
- `langgraph.json` -- new graph registration
- `vite.config.ts` -- new proxy for sandbox API routes
- New files under `src/patterns/deep-agent-ide/`
- New files under `packages/agent/` for sandbox API (or integrate into existing agent structure)
