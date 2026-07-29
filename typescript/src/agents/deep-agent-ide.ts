import { createDeepAgent, type SandboxBackendProtocolV2 } from "deepagents";

import { getOrCreateSandboxForThread, SECURITY_INSTRUCTIONS } from "../api/utils.js";

// [AGC:START] tool=Cc author=fangkun

/** Lazy backend proxy that resolves the sandbox on first use. */
class LazySandboxBackend implements SandboxBackendProtocolV2 {
  #threadId: string | null = null;
  #backend: Promise<SandboxBackendProtocolV2> | null = null;

  setThreadId(id: string): void {
    this.#threadId = id;
  }

  #resolve(): Promise<SandboxBackendProtocolV2> {
    if (!this.#backend) {
      if (!this.#threadId) {
        this.#backend = Promise.reject(new Error("threadId not set — call setThreadId before using the sandbox"));
        return this.#backend;
      }
      this.#backend = getOrCreateSandboxForThread(this.#threadId);
    }
    return this.#backend;
  }

  get id(): string {
    return this.#threadId ?? "lazy-sandbox";
  }

  async ls(path: string) { return this.#resolve().then(b => b.ls(path)); }
  async read(filePath: string, offset?: number, limit?: number) { return this.#resolve().then(b => b.read(filePath, offset, limit)); }
  async readRaw(filePath: string) { return this.#resolve().then(b => b.readRaw(filePath)); }
  async grep(pattern: string, path?: string | null, glob?: string | null) { return this.#resolve().then(b => b.grep(pattern, path, glob)); }
  async glob(pattern: string, path?: string) { return this.#resolve().then(b => b.glob(pattern, path)); }
  async delete(filePath?: string) { return this.#resolve().then(b => b.delete?.(filePath!)); }
  async execute(command: string) { return this.#resolve().then(b => b.execute(command)); }
}

const lazyBackend = new LazySandboxBackend();

const modelEnv = process.env.OPENAI_MODEL || "qwen3.5-plus";
const model = `openai:${modelEnv}`;

export const agent = createDeepAgent({
  model,
  backend: lazyBackend,
  name: "deep-agent-ide",
  systemPrompt: `You are an expert Node.js developer working on a project in /app.
The project is a simple REST API for managing todos.

When making changes:
- Read existing files first to understand the current state
- Make targeted edits rather than rewriting entire files
- Run tests after making changes if tests exist
- Explain what you changed and why

The project structure:
/app/
  package.json
  README.md
  src/
    index.js     — HTTP server entry point
    store.js     — In-memory todo storage
    router.js    — Request routing and handlers

${SECURITY_INSTRUCTIONS}`,
}).withConfig({
  recursionLimit: 200,
});

/** Set the thread ID so the lazy backend can resolve the sandbox. */
export function setSandboxThreadId(id: string): void {
  lazyBackend.setThreadId(id);
}
// [AGC:END]