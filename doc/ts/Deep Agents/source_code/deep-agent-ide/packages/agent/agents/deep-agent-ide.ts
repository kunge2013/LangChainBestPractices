import { createDeepAgent } from "deepagents";
import type { LangGraphRunnableConfig } from "@langchain/langgraph";

import { getOrCreateSandboxForThread, SECURITY_INSTRUCTIONS } from "../api/utils.js";

export async function agent(runtime: LangGraphRunnableConfig) {
  const threadId = runtime.configurable?.thread_id as string;
  const backend = await getOrCreateSandboxForThread(threadId);

  return createDeepAgent({
    model: "anthropic:claude-haiku-4-5",
    backend,
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
