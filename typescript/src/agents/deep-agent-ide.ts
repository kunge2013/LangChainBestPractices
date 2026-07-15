import { createDeepAgent } from "deepagents";
import type { LangGraphRunnableConfig } from "@langchain/langgraph";

import { getOrCreateSandboxForThread, SECURITY_INSTRUCTIONS } from "../api/utils.js";

// [AGC:START] tool=Cc author=fangkun
export async function agent(runtime: LangGraphRunnableConfig) {
  const threadId = runtime.configurable?.thread_id as string | undefined;
  if (!threadId) {
    throw new Error("deep-agent-ide requires a thread_id in runtime.configurable");
  }
  const backend = await getOrCreateSandboxForThread(threadId);

  const modelEnv = process.env.OPENAI_MODEL || "qwen3.5-plus";
  const model = `openai:${modelEnv}`;

  return createDeepAgent({
    model,
    backend,
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
}
// [AGC:END]