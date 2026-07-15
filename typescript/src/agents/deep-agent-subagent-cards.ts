import { createDeepAgent } from "deepagents";

// [AGC:START] tool=Cc author=fangkun
const modelEnv = process.env.OPENAI_MODEL || "qwen3.5-plus";
const model = `openai:${modelEnv}`;

const agent = createDeepAgent({
  model,
  name: "deep_agent_subagent_cards",
  systemPrompt: `You are a deep agent that orchestrates subagents to solve complex tasks.
You will spawn 2-3 parallel subagents to work independently:

1. **researcher**: Gathers relevant information and facts
2. **analyzer**: Analyzes and synthesizes the research findings
3. **writer**: Produces a well-structured report based on the analysis

Each subagent should work on its assigned task independently. Once all subagents complete,
you synthesize their outputs into a comprehensive response.`,
  subagents: [
    {
      name: "researcher",
      description: "Gathers relevant information and facts for the task",
      systemPrompt: `You are a researcher. Your role is to gather relevant information and facts
to help answer the user's question. Focus on finding accurate, reliable sources.`,
    },
    {
      name: "analyzer",
      description: "Analyzes and synthesizes research findings",
      systemPrompt: `You are an analyzer. Your role is to analyze and synthesize the research
findings provided to you. Identify key insights, patterns, and connections.`,
    },
    {
      name: "writer",
      description: "Produces a well-structured report",
      systemPrompt: `You are a writer. Your role is to produce a well-structured, clear report
that synthesizes the research and analysis into actionable insights.`,
    },
  ],
});
// [AGC:END]

export { agent };
