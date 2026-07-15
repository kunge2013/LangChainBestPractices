export interface AgentState {
  messages: Array<{ type: string; content: string; id?: string }>;
}
