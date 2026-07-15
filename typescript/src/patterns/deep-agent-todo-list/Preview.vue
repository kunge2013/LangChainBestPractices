<script setup lang="ts">
import { computed, ref } from "vue";
import { useStream, type SubagentDiscoverySnapshot } from "@langchain/vue";
import { HumanMessage, AIMessage } from "langchain";
import type { deepAgentTodoListAgent } from "@langchain/playground-agents";

import { SLUG_TO_ASSISTANT } from "@/constants";
import {
  ChatContainer,
  SplitView,
  HumanBubble,
  AIBubble,
  ChatInput,
  TypingIndicator,
  PresetPrompts,
  Markdown,
  SubAgentCard,
} from "@/components/playground";
import TodoList from "./TodoList.vue";

const PRESETS = [
  "Plan a weekend trip to the beach for a family of four",
  "Organize a small birthday party for a 10-year-old",
];

const threadId = ref<string | null>(null);
const stream = useStream<typeof deepAgentTodoListAgent>({
  assistantId: SLUG_TO_ASSISTANT["deep-agent-todo-list"],
  threadId,
  onThreadId: (id: string) => {
    threadId.value = id;
  },
});

function handleSubmit(text: string) {
  stream.submit({ messages: [{ type: "human" as const, content: text }] });
}

function handleNewThread() {
  threadId.value = null;
}

const messages = computed(() => stream.messages.value ?? []);
const todos = computed(() => stream.values.value?.todos ?? []);
const subagentList = computed<SubagentDiscoverySnapshot[]>(() =>
  Array.from(stream.subagents.value.values()),
);
const hasSubagents = computed(() => subagentList.value.length > 0);
const completedCount = computed(
  () => subagentList.value.filter((s) => s.status === "complete").length,
);
const totalCount = computed(() => subagentList.value.length);
const allSubagentsDone = computed(
  () =>
    hasSubagents.value &&
    subagentList.value.every((s) => s.status === "complete" || s.status === "error"),
);
</script>

<template>
  <SplitView :sidebarWidth="300">
    <template #main>
      <ChatContainer embedded>
        <PresetPrompts
          v-if="messages.length === 0 && !hasSubagents"
          :prompts="PRESETS"
          @select="handleSubmit"
        />

        <template v-for="(msg, i) in messages" :key="msg.id ?? i">
          <HumanBubble v-if="HumanMessage.isInstance(msg)">
            <Markdown :content="msg.text" />
          </HumanBubble>
          <AIBubble v-else-if="AIMessage.isInstance(msg) && msg.text.trim().length > 0">
            <Markdown :content="msg.text" />
          </AIBubble>
        </template>

        <div v-if="hasSubagents" class="mt-3 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-text-secondary">
              Specialist agents &middot; {{ completedCount }}/{{ totalCount }} completed
            </span>
          </div>

          <div class="w-full h-1 rounded-full bg-surface-tertiary overflow-hidden">
            <div
              class="h-full rounded-full bg-primary transition-all duration-500"
              :style="{ width: `${totalCount ? (completedCount / totalCount) * 100 : 0}%` }"
            />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            <SubAgentCard
              v-for="subagent in subagentList"
              :key="subagent.id"
              :stream="stream"
              :subagent="subagent"
            />
          </div>
        </div>

        <TypingIndicator v-if="stream.isLoading.value && !hasSubagents" />

        <div
          v-if="stream.isLoading.value && allSubagentsDone"
          class="flex items-center gap-2 text-text-tertiary animate-pulse text-sm"
        >
          <span class="inline-block w-4 h-4">&#10022;</span>
          Synthesizing results…
        </div>

        <template #input>
          <ChatInput
            @submit="handleSubmit"
            :disabled="stream.isLoading.value"
            :showNewThread="messages.length > 0"
            @newThread="handleNewThread"
          />
        </template>
      </ChatContainer>
    </template>

    <template #sidebar>
      <div class="bg-surface p-4">
        <TodoList v-if="todos.length > 0" :todos="todos" />
        <p v-else class="text-xs text-text-tertiary">Tasks will appear here as the agent plans.</p>
      </div>
    </template>
  </SplitView>
</template>
