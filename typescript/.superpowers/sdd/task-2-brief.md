# Task 2 Brief: Sandbox API

**Context:** This is Task 2 of 7 in the deep-agent-ide integration. Task 1 completed (dependencies, config, proxy). Now we create the Hono-based sandbox API that serves REST routes for file operations (tree, file content, directory listing, sandbox info).

**Where this fits:** The sandbox API runs as a Hono app registered in langgraph.json's `http.app` field. It serves routes that the frontend's `useSandboxFiles` composable calls to fetch file trees, read files, and track sandbox status.

**Goal:** Create 4 new files in `src/api/` that implement the sandbox REST API using Hono, with LocalShellBackend for local development.

**Global Constraints:**
- Model: `openai:${process.env.OPENAI_MODEL || "qwen3.5-plus"}` (matching existing agent)
- Sandbox: LocalShellBackend only (dev mode, NODE_ENV=development)
- Package manager: pnpm
- Node version: 22
- Path alias: `@/*` maps to `src/*`
- Agent code prefix: `// [AGC:START] tool=Cc author=fangkun` / `// [AGC:END]`
- DRY, YAGNI, frequent commits

## Files to Create

### 1. `src/api/sandbox-security.ts`
Security utilities for sandbox environment management. Contains:
- `isDevelopmentEnvironment()` - checks NODE_ENV
- `LocalSandboxNotAllowedError` class
- `RemoteSandboxUnavailableError` class
- `resolveSandboxBackendMode()` - resolves SANDBOX_BACKEND env var
- `assertLocalSandboxAllowed()` - throws if not in dev mode
- `handleRemoteSandboxAuthFailure()` - handles 403 in dev
- `getLocalSandboxEnv()` - minimal env allowlist for local sandboxes
- `createLocalShellBackendOptions()` - creates options for LocalShellBackend

### 2. `src/api/utils.ts`
Sandbox management and seed data. Contains:
- `SAMPLE_PROJECT` - Record of sample project files (package.json, README.md, src/index.js, src/store.js, src/router.js)
- `sampleProjectInitialFiles()` - converts sample project to sandbox paths
- `getOrCreateLocalSandboxForThread()` - creates/reuses LocalShellBackend per thread
- `getLanggraphClient()` - creates LangGraph client
- `getOrCreateSandboxForThread()` - main entry point, wraps with hardenSandbox
- `SECURITY_INSTRUCTIONS` - prompt injection prevention rules
- `_resetSandboxStateForTesting()` - test hook
- `hardenSandbox()` - minimal pass-through wrapper

### 3. `src/api/sandbox.ts`
Hono route registrations. Contains:
- `registerSandbox(app: Hono)` - registers 4 routes:
  - `GET /sandbox/:threadId/ls` - directory listing
  - `GET /sandbox/:threadId/tree` - full file tree (glob)
  - `GET /sandbox/:threadId/file` - single file content
  - `GET /sandbox/:threadId/info` - sandbox status
- Path validation, thread ID validation, path normalization utilities
- FileEntry interface, sorting, and listing helpers

### 4. `src/api/app.ts`
Hono app aggregator. Contains:
- Imports Hono and registerSandbox
- Exports `app = new Hono()`
- Calls `registerSandbox(app)`

## Steps

1. Create `src/api/sandbox-security.ts` (copy exact content from plan Task 2, Step 1)
2. Create `src/api/utils.ts` (copy exact content from plan Task 2, Step 2)
3. Create `src/api/sandbox.ts` (copy exact content from plan Task 2, Step 3)
4. Create `src/api/app.ts` (copy exact content from plan Task 2, Step 4)
5. Verify TypeScript compilation: `npx vue-tsc --noEmit`
6. Commit: `git add src/api/ && git commit -m "feat: add sandbox API routes with Hono"`

## Report

Write to: `.superpowers/sdd/task-2-report.md`
Return: status, commits, test summary, concerns
