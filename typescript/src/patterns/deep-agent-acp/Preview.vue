<script setup lang="ts">
import { computed, ref } from "vue";
import { useStream } from "@langchain/vue";
import { HumanMessage, AIMessage } from "langchain";
import type { deepAgentAcpAgent } from "@langchain/playground-agents";

import { SLUG_TO_ASSISTANT } from "@/constants";
import {
  ChatContainer,
  HumanBubble,
  AIBubble,
  ChatInput,
  TypingIndicator,
  PresetPrompts,
  Markdown,
} from "@/components/playground";

const PRESETS = [
  "Explain the difference between REST and GraphQL",
  "Write a simple Express server with a /health endpoint",
];

const threadId = ref<string | null>(null);

const stream = useStream<typeof deepAgentAcpAgent>({
  assistantId: SLUG_TO_ASSISTANT["deep-agent-acp"],
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
</script>

<template>
  <ChatContainer>
    <PresetPrompts
      v-if="messages.length === 0"
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

    <TypingIndicator v-if="stream.isLoading.value" />

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
