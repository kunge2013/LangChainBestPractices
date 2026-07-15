import type { BaseMessage } from "langchain";

export interface TodoItem {
  title: string;
  status: "pending" | "in_progress" | "completed";
  description?: string;
}

export interface AgentState {
  messages: BaseMessage[];
  todos: TodoItem[];
}
