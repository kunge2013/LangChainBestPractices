# Tasks: Integrate Deep Agent IDE

## Phase 1: Copy Source Files

- [ ] 1.1 Copy `deep-agent-ide` frontend pattern files into `src/patterns/deep-agent-ide/`
  - `Preview.vue`, `ChatPanel.vue`, `CodePanel.vue`, `FileTree.vue`, `FileTreeItem.vue`, `FileIcon.vue`, `file-icon.ts`, `ChangedFilesSummary.vue`, `types.ts`, `use-sandbox-files.ts`
- [ ] 1.2 Copy sandbox API files into `src/api/`
  - `sandbox.ts`, `sandbox-security.ts`, `utils.ts`
- [ ] 1.3 Create `src/api/app.ts` (Hono app aggregator)
- [ ] 1.4 Create `hardened-sandbox.ts` stub (missing in source; implement basic noop wrapper)

## Phase 2: Agent Definition

- [ ] 2.1 Create `src/agents/deep-agent-ide.ts`
  - Use `createDeepAgent` with `openai:${OPENAI_MODEL}` model (matching existing pattern)
  - Import sandbox utilities and configure backend
  - Export `agent` function matching LangGraph contract
- [ ] 2.2 Update `langgraph.json`
  - Add `"deep_agent_ide": "./src/agents/deep-agent-ide.ts:agent"` to graphs
  - Add `"http": { "app": "./src/api/app.ts:app" }` for sandbox routes

## Phase 3: Frontend Integration

- [ ] 3.1 Update `src/agent-config.ts`
  - Add `"deep-agent-ide": "deep_agent_ide"` to `SLUG_TO_ASSISTANT` map
- [ ] 3.2 Update `src/constants.ts` if needed (re-exports from agent-config)
- [ ] 3.3 Update `src/App.vue`
  - Add top navigation bar with tabs for switching between patterns
  - Render selected pattern's `Preview.vue`
  - Use CSS tokens from `shared-styles/tokens.css` for styling
- [ ] 3.4 Update `src/components/playground.ts`
  - Re-export any new IDE components if needed by other patterns

## Phase 4: Build Configuration

- [ ] 4.1 Update `vite.config.ts`
  - Add proxy for `/sandbox/:threadId/*` routes to localhost:2024
  - Verify existing `/api/langgraph` and `/threads` proxies are sufficient
- [ ] 4.2 Update `package.json`
  - Verify all required dependencies are present (should already have most from existing setup)
  - Add `@langchain/anthropic` if needed (only if agent still references it)
- [ ] 4.3 Update `langgraph.json` CORS if needed

## Phase 5: Verify & Test

- [ ] 5.1 Run `pnpm install` to sync dependencies
- [ ] 5.2 Run `pnpm run dev` and verify both agents start
- [ ] 5.3 Test navigation between Subagent Cards and IDE patterns
- [ ] 5.4 Test IDE pattern: send a prompt, verify agent responds, verify file tree/sandbox works
- [ ] 5.5 Run `pnpm run build` to verify production build succeeds
