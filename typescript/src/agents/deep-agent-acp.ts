import { createDeepAgent } from "deepagents";

// [AGC:START] tool=Cc author=fangkun
const modelEnv = process.env.OPENAI_MODEL || "qwen3.5-plus";
const model = `openai:${modelEnv}`;

const agent = createDeepAgent({
  model,
  name: "deep_agent_acp",
  systemPrompt: `You are an AI coding assistant that follows the Agent Client Protocol (ACP).
You help users with coding tasks including code understanding, writing, debugging, and project management.
You can read files, write code, execute commands, and provide helpful explanations.
Always be thorough and provide clear, well-structured responses.`,
});
// [AGC:END]

export { agent };
