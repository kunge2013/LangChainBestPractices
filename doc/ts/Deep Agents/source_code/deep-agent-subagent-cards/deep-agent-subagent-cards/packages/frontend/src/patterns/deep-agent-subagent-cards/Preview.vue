<script setup lang="ts">
import { computed, ref } from "vue";
import { useStream, type AnyStream, type SubagentDiscoverySnapshot } from "@langchain/vue";
import { HumanMessage, AIMessage } from "langchain";
import type { deepAgentSubagentCardsAgent } from "@langchain/playground-agents";

const DEEP_AGENT_SUBAGENT_CARDS_THREAD_STORAGE_KEY = "subagent-cards-thread-id";
import { SLUG_TO_ASSISTANT } from "@/constants";
import {
  ChatContainer,
  HumanBubble,
  AIBubble,
  ChatInput,
  TypingIndicator,
  PresetPrompts,
  Markdown,
  SubAgentCard,
} from "@/components/playground";

const PRESETS = [
  "Compare React, Vue, and Svelte for building a new team dashboard",
  "Give a quick briefing on recent trends in AI, clean energy, and cybersecurity",
];

const threadId = ref<string | null>(
  typeof sessionStorage !== "undefined"
    ? sessionStorage.getItem(DEEP_AGENT_SUBAGENT_CARDS_THREAD_STORAGE_KEY)
    : null,
);

function updateThreadId(id: string | null) {
  threadId.value = id;
  if (typeof sessionStorage === "undefined") return;
  if (id) {
    sessionStorage.setItem(DEEP_AGENT_SUBAGENT_CARDS_THREAD_STORAGE_KEY, id);
  } else {
    sessionStorage.removeItem(DEEP_AGENT_SUBAGENT_CARDS_THREAD_STORAGE_KEY);
  }
}

const stream = useStream<typeof deepAgentSubagentCardsAgent>({
  assistantId: SLUG_TO_ASSISTANT["deep-agent-subagent-cards"],
  threadId,
  onThreadId: (id: string) => updateThreadId(id),
});

function handleSubmit(text: string) {
  stream.submit({ messages: [{ type: "human" as const, content: text }] });
}

function handleNewThread() {
  updateThreadId(null);
}

const subagentList = computed<SubagentDiscoverySnapshot[]>(() =>
  Array.from(stream.subagents.value.values()),
);

// Group discovery snapshots under the AI message whose tool_call spawned them.
function subagentsForMessage(msg: AIMessage): SubagentDiscoverySnapshot[] {
  const toolCallIds = new Set((msg.tool_calls ?? []).map((t) => t.id).filter(Boolean) as string[]);
  return subagentList.value.filter((s) => toolCallIds.has(s.id));
}

const messages = computed(() =>
  stream.messages.value.filter((msg) => {
    if (HumanMessage.isInstance(msg)) return true;
    if (AIMessage.isInstance(msg)) {
      return msg.text.trim().length > 0 || subagentsForMessage(msg).length > 0;
    }
    return false;
  }),
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
  <ChatContainer>
    <PresetPrompts
      v-if="messages.length === 0 && !hasSubagents"
      :prompts="PRESETS"
      @select="handleSubmit"
    />

    <div v-for="(msg, i) in messages" :key="msg.id ?? `msg-${i}`">
      <HumanBubble v-if="HumanMessage.isInstance(msg)">
        <Markdown :content="msg.text" />
      </HumanBubble>

      <AIBubble v-if="AIMessage.isInstance(msg) && msg.text.trim().length > 0">
        <Markdown :content="msg.text" />
      </AIBubble>

      <template v-if="AIMessage.isInstance(msg) && subagentsForMessage(msg).length > 0">
        <div class="mt-3 space-y-3">
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
            <template v-for="subagent in subagentsForMessage(msg)" :key="subagent.id">
              <SubAgentCard
                v-if="subagent.namespace.length > 0"
                :stream="stream as AnyStream"
                :subagent="subagent"
              />
            </template>
          </div>
        </div>
      </template>
    </div>

    <TypingIndicator v-if="stream.isLoading.value && !hasSubagents" />

    <div
      v-if="stream.isLoading.value && allSubagentsDone"
      class="flex items-center gap-2 text-text-tertiary animate-pulse text-sm"
    >
      <span class="inline-block w-4 h-4">✦</span>
      Synthesizing results…
    </div>

    <template #input>
      <ChatInput
        @submit="handleSubmit"
        :disabled="stream.isLoading.value"
        :showNewThread="stream.messages.value.length > 0"
        @newThread="handleNewThread"
      />
    </template>
  </ChatContainer>
</template>
