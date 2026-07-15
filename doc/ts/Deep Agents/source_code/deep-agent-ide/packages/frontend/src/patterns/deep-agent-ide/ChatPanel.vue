<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { HumanMessage, AIMessage, ToolMessage } from "langchain";
import { formatDeepAgentRunError } from "@langchain/playground-preview-protocol";

import { Markdown } from "@/components/playground";

const EXAMPLE_PROMPTS = [
  "Add input validation — reject empty titles and trim whitespace",
  "Add a GET /todos/search?q= endpoint with fuzzy title matching",
  "Add pagination support: GET /todos?page=1&limit=10",
  "Add a /health endpoint that returns server uptime and todo count",
  "Add unit tests for the TodoStore class",
];

const COMPACT_TOOLS = new Set(["read_file", "ls", "glob", "grep"]);

const props = defineProps<{
  messages: unknown[];
  isLoading: boolean;
  error?: unknown;
  showNewThread?: boolean;
}>();

const emit = defineEmits<{
  submit: [text: string];
  newThread: [];
}>();

defineExpose({});

const scrollRef = ref<HTMLDivElement | null>(null);
const text = ref("");

watch(
  () => props.messages.length,
  async () => {
    await nextTick();
    const el = scrollRef.value;
    if (el) el.scrollTop = el.scrollHeight;
  },
);

function handleSubmit(e: Event) {
  e.preventDefault();
  const trimmed = text.value.trim();
  if (!trimmed || props.isLoading) return;
  emit("submit", trimmed);
  text.value = "";
}

function extractTextContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((block) => {
        if (typeof block === "string") return block;
        if (block && typeof block === "object" && "text" in block) return String(block.text);
        return "";
      })
      .join("\n");
  }
  return String(content);
}

function extractReadFileSummary(
  toolCallArgs: Record<string, unknown> | undefined,
  content: unknown,
): string | null {
  if (!toolCallArgs) return null;
  const filePath = (toolCallArgs.path ?? toolCallArgs.file_path) as string | undefined;
  const fileName = filePath?.split("/").pop() ?? filePath ?? "file";
  const textStr = extractTextContent(content);
  const lines = textStr.split("\n").filter(Boolean);
  const lineCount = lines.length;
  if (lineCount === 0) return `Read ${fileName}`;
  return `Read ${fileName} L1-${lineCount}`;
}

function extractCompactToolSummary(
  toolName: string,
  toolCallArgs: Record<string, unknown> | undefined,
  content: unknown,
): string | null {
  if (toolName === "read_file") return extractReadFileSummary(toolCallArgs, content);
  if (toolName === "ls") {
    const dir = (toolCallArgs?.path as string)?.split("/").pop() ?? "";
    return `ls ${dir || "/"}`;
  }
  if (toolName === "glob" || toolName === "grep") {
    const pattern = (toolCallArgs?.pattern ?? toolCallArgs?.glob ?? "") as string;
    return `${toolName} ${pattern}`;
  }
  return null;
}

const toolCallMap = computed(() => {
  const map = new Map<string, { name: string; args: Record<string, unknown> }>();
  for (const msg of props.messages) {
    if (AIMessage.isInstance(msg)) {
      for (const tc of (msg as AIMessage).tool_calls ?? []) {
        if (tc.id) map.set(tc.id, { name: tc.name, args: tc.args as Record<string, unknown> });
      }
    }
  }
  return map;
});

const completedToolCallIds = computed(() => {
  const ids = new Set<string>();
  for (const msg of props.messages) {
    if (ToolMessage.isInstance(msg)) {
      const toolCallId = (msg as ToolMessage).tool_call_id;
      if (toolCallId) ids.add(toolCallId);
    }
  }
  return ids;
});

const isEmpty = computed(() => props.messages.length === 0);
const formattedError = computed(() => formatDeepAgentRunError(props.error));

function isCompactTool(toolName: string): boolean {
  return COMPACT_TOOLS.has(toolName);
}

function getCompactSummary(toolMsg: ToolMessage): string | null {
  const toolName = toolMsg.name || "";
  const matchingCall = toolCallMap.value.get(toolMsg.tool_call_id);
  return extractCompactToolSummary(toolName, matchingCall?.args, toolMsg.content);
}

function getPendingToolCalls(msg: AIMessage) {
  return (msg.tool_calls ?? []).filter((tc) => tc.id && !completedToolCallIds.value.has(tc.id));
}

function getToolContent(toolMsg: ToolMessage): string {
  return typeof toolMsg.content === "string"
    ? toolMsg.content.slice(0, 500)
    : JSON.stringify(toolMsg.content).slice(0, 500);
}
</script>

<template>
  <div
    class="flex flex-col h-full bg-zinc-50 dark:bg-zinc-900 border-l border-zinc-200 dark:border-zinc-700/50"
  >
    <div
      class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 border-b border-zinc-200 dark:border-zinc-700/50 flex items-center justify-between"
    >
      <span>Agent</span>
      <button
        v-if="showNewThread"
        type="button"
        @click="emit('newThread')"
        class="text-zinc-400 dark:text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors cursor-pointer normal-case tracking-normal font-normal"
      >
        + New
      </button>
    </div>

    <div ref="scrollRef" class="flex-1 overflow-y-auto px-3 py-3 space-y-3">
      <div v-if="isEmpty" class="space-y-3">
        <div class="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
          Ask the agent to modify the todo-api project. Try one of these:
        </div>
        <div class="space-y-1.5">
          <button
            v-for="prompt in EXAMPLE_PROMPTS"
            :key="prompt"
            type="button"
            @click="emit('submit', prompt)"
            :disabled="isLoading"
            class="w-full text-left px-2.5 py-2 text-xs text-zinc-500 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700/50 rounded hover:border-blue-500/50 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors cursor-pointer disabled:opacity-40"
          >
            {{ prompt }}
          </button>
        </div>
      </div>

      <template v-for="(msg, i) in messages" :key="(msg as any).id ?? `msg-${i}`">
        <div v-if="HumanMessage.isInstance(msg)" class="flex justify-end">
          <div
            class="max-w-[85%] bg-blue-600 text-white rounded-lg rounded-br-sm px-3 py-2 text-xs leading-relaxed"
          >
            {{ (msg as HumanMessage).text }}
          </div>
        </div>

        <template v-else-if="ToolMessage.isInstance(msg)">
          <div
            v-if="
              isCompactTool((msg as ToolMessage).name || '') &&
              getCompactSummary(msg as ToolMessage)
            "
            class="pl-2"
          >
            <div class="text-[10px] font-mono text-zinc-400 dark:text-zinc-500">
              ↳ {{ getCompactSummary(msg as ToolMessage) }}
            </div>
          </div>
          <div v-else class="pl-2">
            <div
              class="bg-zinc-100 dark:bg-zinc-800/50 border border-zinc-200/60 dark:border-zinc-700/30 rounded px-2.5 py-1.5 text-[10px] font-mono text-zinc-500 dark:text-zinc-400 max-h-24 overflow-y-auto"
            >
              <div class="text-zinc-400 dark:text-zinc-500 mb-0.5">
                ↳ {{ (msg as ToolMessage).name || "tool result" }}
              </div>
              <pre class="whitespace-pre-wrap break-all">{{
                getToolContent(msg as ToolMessage)
              }}</pre>
            </div>
          </div>
        </template>

        <div v-else-if="AIMessage.isInstance(msg)" class="space-y-1.5">
          <template
            v-if="
              (msg as AIMessage).text.trim() || getPendingToolCalls(msg as AIMessage).length > 0
            "
          >
            <div
              v-if="(msg as AIMessage).text.trim()"
              class="bg-zinc-100 dark:bg-zinc-800/50 border border-zinc-200/60 dark:border-zinc-700/30 rounded-lg rounded-bl-sm px-3 py-2 text-xs leading-relaxed text-zinc-700 dark:text-zinc-300"
            >
              <Markdown :content="(msg as AIMessage).text" />
            </div>
            <div
              v-if="getPendingToolCalls(msg as AIMessage).length > 0"
              class="flex flex-wrap gap-1 pl-1"
            >
              <div
                v-for="tc in getPendingToolCalls(msg as AIMessage)"
                :key="tc.id"
                class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono text-blue-600 dark:text-blue-400 bg-blue-500/10 dark:bg-blue-400/10"
              >
                ⟳ {{ tc.name }}
              </div>
            </div>
          </template>
        </div>
      </template>

      <div
        v-if="formattedError && !isLoading"
        class="rounded-lg border px-3 py-2 text-xs leading-relaxed"
        :class="
          formattedError.variant === 'security'
            ? 'border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-200'
            : 'border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300'
        "
      >
        <div class="font-semibold">{{ formattedError.title }}</div>
        <p class="mt-1 whitespace-pre-wrap break-words opacity-90">{{ formattedError.message }}</p>
      </div>

      <div
        v-if="isLoading"
        class="flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500"
      >
        <div
          class="animate-spin w-3 h-3 border border-zinc-300 dark:border-zinc-600 border-t-zinc-600 dark:border-t-zinc-300 rounded-full"
        />
        Working…
      </div>
    </div>

    <div class="border-t border-zinc-200 dark:border-zinc-700/50 px-3 py-2">
      <form @submit="handleSubmit" class="flex gap-2">
        <input
          type="text"
          v-model="text"
          placeholder="Ask the agent to modify files…"
          :disabled="isLoading"
          class="flex-1 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded px-2.5 py-1.5 text-xs text-zinc-800 dark:text-zinc-200 placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:border-blue-500/50 disabled:opacity-50"
        />
        <button
          type="submit"
          :disabled="isLoading || !text.trim()"
          class="bg-blue-600 text-white px-3 py-1.5 rounded text-xs font-medium hover:bg-blue-500 disabled:opacity-40 transition-colors cursor-pointer"
        >
          Send
        </button>
      </form>
    </div>
  </div>
</template>
