<script setup lang="ts">
import { ref, computed, watch, onUpdated } from "vue";
import { AIMessage } from "langchain";
import {
  useMessages,
  useToolCalls,
  type AnyStream,
  type AssembledToolCall,
  type SubagentDiscoverySnapshot,
} from "@langchain/vue";

import StatusBadge from "../../components/cards/StatusBadge.vue";
import Markdown from "../../components/Markdown.vue";

const props = defineProps<{
  stream: AnyStream;
  subagent: SubagentDiscoverySnapshot;
}>();

// Pass a getter so namespace updates rebind the scoped subscription.
const subagentMessages = useMessages(props.stream, () => props.subagent);
const toolCalls = useToolCalls(props.stream, () => props.subagent);

const scrollRef = ref<HTMLDivElement>();
const open = ref(true);

const statusMap: Record<string, "pending" | "running" | "complete" | "error"> = {
  pending: "pending",
  running: "running",
  complete: "complete",
  error: "error",
};

const status = computed(() => statusMap[props.subagent.status] ?? "running");

type ContentItem =
  | { kind: "text"; content: string; key: string }
  | { kind: "tool_call"; call: AssembledToolCall; key: string };

const contentItems = computed<ContentItem[]>(() => {
  const items: ContentItem[] = [];
  const seenToolCallIds = new Set<string>();

  for (const msg of subagentMessages.value) {
    if (!AIMessage.isInstance(msg)) continue;
    if (msg.text.trim()) {
      items.push({ kind: "text", content: msg.text, key: `text-${msg.id}` });
    }
    const msgToolCallIds = new Set(msg.tool_calls?.map((t) => t.id) ?? []);
    for (const tc of toolCalls.value) {
      if (msgToolCallIds.has(tc.callId) && !seenToolCallIds.has(tc.callId)) {
        seenToolCallIds.add(tc.callId);
        items.push({ kind: "tool_call", call: tc, key: `tc-${tc.callId}` });
      }
    }
  }

  return items;
});

const taskDescription = computed(() => props.subagent.taskInput ?? "Working on task…");
const title = computed(() => props.subagent.name ?? "Subagent");

watch(status, (s) => {
  if (s === "running") open.value = true;
});

onUpdated(() => {
  if (scrollRef.value && status.value === "running") {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
  }
});

function formatDuration(startedAt: Date, completedAt: Date): string {
  const ms = completedAt.getTime() - startedAt.getTime();
  return `${(ms / 1000).toFixed(1)}s`;
}

const toolStateStyles: Record<AssembledToolCall["status"], string> = {
  running: "text-primary",
  finished: "text-emerald-600 dark:text-emerald-400",
  error: "text-error",
};
</script>

<template>
  <div
    class="rounded-lg border border-border bg-surface-secondary overflow-hidden flex flex-col"
    data-testid="sdk-preview-chat-turn"
  >
    <button
      type="button"
      @click="open = !open"
      class="flex w-full items-center justify-between px-3 py-2 text-sm font-medium text-text hover:bg-surface-tertiary transition-colors"
    >
      <span class="flex items-center gap-2 min-w-0">
        <span :class="['text-xs transition-transform', open ? 'rotate-90' : '']">▶</span>
        <span class="truncate">{{ title }}</span>
      </span>
      <StatusBadge :status="status" />
    </button>

    <div v-if="open" class="border-t border-border flex flex-col min-h-0">
      <p class="px-3 pt-2 pb-1 text-xs text-text-tertiary truncate m-0">{{ taskDescription }}</p>

      <div ref="scrollRef" class="px-3 py-2 overflow-y-auto space-y-1.5" style="max-height: 12rem">
        <template v-for="(item, i) in contentItems" :key="item.key">
          <div v-if="item.kind === 'text'" class="text-sm text-text-secondary">
            <Markdown :content="item.content" />
            <span
              v-if="status === 'running' && i === contentItems.length - 1"
              class="animate-pulse ml-0.5 text-primary"
              >▌</span
            >
          </div>
          <div
            v-else
            :class="['flex items-center gap-1.5 text-xs', toolStateStyles[item.call.status]]"
          >
            <span class="font-mono font-semibold truncate">{{ item.call.name }}</span>
          </div>
        </template>

        <div
          v-if="contentItems.length === 0 && (status === 'running' || status === 'pending')"
          class="flex items-center gap-1.5 text-text-tertiary"
        >
          <span
            v-for="i in [0, 1, 2]"
            :key="i"
            class="w-1.5 h-1.5 rounded-full bg-current animate-bounce"
            :style="{ animationDelay: `${i * 150}ms` }"
          />
          <span class="text-xs ml-1">{{ status === "pending" ? "Queued…" : "Working…" }}</span>
        </div>
        <p
          v-else-if="contentItems.length === 0 && status === 'error'"
          class="text-xs text-error m-0"
        >
          {{ subagent.error ?? "An error occurred while running this subagent." }}
        </p>
      </div>

      <div
        v-if="subagent.startedAt"
        class="px-3 py-1.5 border-t border-border text-xs text-text-tertiary"
      >
        <span v-if="subagent.completedAt"
          >Completed in {{ formatDuration(subagent.startedAt, subagent.completedAt) }}</span
        >
        <span v-else>Started at {{ subagent.startedAt.toLocaleTimeString() }}</span>
      </div>
    </div>
  </div>
</template>
