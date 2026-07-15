<script setup lang="ts">
import { ref, watch, computed, inject } from "vue";
import { useStream } from "@langchain/vue";
import { ToolMessage, AIMessage } from "langchain";
import type { deepAgentIdeAgent } from "@langchain/playground-agents";
const DEEP_AGENT_SANDBOX_THREAD_STORAGE_KEY = "sandbox-thread-id";

import { AGENT_SERVER_URL, SLUG_TO_ASSISTANT } from "@/constants";

import FileTree from "./FileTree.vue";
import CodePanel from "./CodePanel.vue";
import ChatPanel from "./ChatPanel.vue";
import ChangedFilesSummary from "./ChangedFilesSummary.vue";
import { useSandboxFiles } from "./use-sandbox-files";

const FILE_MUTATING_TOOLS = new Set(["write_file", "edit_file", "execute"]);

function extractFilePathFromToolCall(name: string, args: Record<string, unknown>): string | null {
  if (name === "write_file" || name === "edit_file") {
    const p = args.path ?? args.file_path;
    return typeof p === "string" ? p : null;
  }
  return null;
}

const threadId = ref<string | null>(
  typeof sessionStorage !== "undefined"
    ? sessionStorage.getItem(DEEP_AGENT_SANDBOX_THREAD_STORAGE_KEY)
    : null,
);

function updateThreadId(id: string | null) {
  threadId.value = id;
  if (typeof sessionStorage === "undefined") return;
  if (id) sessionStorage.setItem(DEEP_AGENT_SANDBOX_THREAD_STORAGE_KEY, id);
  else sessionStorage.removeItem(DEEP_AGENT_SANDBOX_THREAD_STORAGE_KEY);
}

const stream = useStream<typeof deepAgentIdeAgent>({
  apiUrl: AGENT_SERVER_URL,
  assistantId: SLUG_TO_ASSISTANT["deep-agent-ide"],
  threadId,
  onThreadId: (id) => updateThreadId(id),
});

// If we don't yet have a thread persisted, mint one eagerly so the sandbox
// composable has a stable id to bind against.
watch(
  threadId,
  () => {
    if (threadId.value) return;
    if (!stream.client) return;
    void stream.client.threads.create().then((t) => {
      updateThreadId(t.thread_id);
    });
  },
  { immediate: true },
);

const {
  tree,
  files,
  originalFiles,
  selectedFile,
  setSelectedFile,
  isLoadingFiles,
  changedFiles,
  takeSnapshot,
  refreshSingleFile,
  refreshTreeAndFiles,
} = useSandboxFiles(threadId);

const viewMode = ref<"code" | "diff">("code");
/** Thread streams accumulate all turns; this offset hides prior chat in the UI. */
const visibleFromIndex = ref(0);
const errorCleared = ref(false);
const lastStreamError = ref(stream.error.value);

watch(
  () => stream.error.value,
  (error) => {
    if (error !== lastStreamError.value) {
      lastStreamError.value = error;
      errorCleared.value = false;
    }
  },
);

const visibleMessages = computed(() => (stream.messages.value ?? []).slice(visibleFromIndex.value));
const visibleError = computed(() => (errorCleared.value ? undefined : stream.error.value));

const processedToolMsgIds = new Set<string>();

watch(
  visibleMessages,
  (messages) => {
    const toolCallMap = new Map<string, { name: string; args: Record<string, unknown> }>();
    for (const msg of messages) {
      if (AIMessage.isInstance(msg)) {
        for (const tc of (msg as AIMessage).tool_calls ?? []) {
          if (tc.id && FILE_MUTATING_TOOLS.has(tc.name)) {
            toolCallMap.set(tc.id, { name: tc.name, args: tc.args as Record<string, unknown> });
          }
        }
      }
    }

    for (const msg of messages) {
      if (!ToolMessage.isInstance(msg)) continue;
      const toolMsg = msg as ToolMessage;
      const msgId = toolMsg.id ?? toolMsg.tool_call_id;
      if (!msgId || processedToolMsgIds.has(msgId)) continue;

      const matchingCall = toolCallMap.get(toolMsg.tool_call_id);
      if (!matchingCall) continue;

      processedToolMsgIds.add(msgId);

      const filePath = extractFilePathFromToolCall(matchingCall.name, matchingCall.args);
      if (filePath) {
        refreshSingleFile(filePath);
      } else if (matchingCall.name === "execute") {
        refreshTreeAndFiles();
      }
    }
  },
  { deep: true },
);

function selectFile(path: string) {
  setSelectedFile(path);
  viewMode.value = changedFiles.value.has(path) ? "diff" : "code";
}

function handleSubmit(text: string) {
  takeSnapshot();
  processedToolMsgIds.clear();
  stream.submit({ messages: [{ type: "human" as const, content: text }] });
}

function handleNewThread() {
  void stream.stop().then(() => {
    visibleFromIndex.value = (stream.messages.value ?? []).length;
    processedToolMsgIds.clear();
    errorCleared.value = true;
});
}

const currentContent = computed(() =>
  selectedFile.value ? files.value[selectedFile.value] : undefined,
);
const originalContent = computed(() =>
  selectedFile.value ? originalFiles.value[selectedFile.value] : undefined,
);
const isChanged = computed(() =>
  selectedFile.value ? changedFiles.value.has(selectedFile.value) : false,
);
const showNewThread = computed(() => visibleMessages.value.length > 0 || !!visibleError.value);
</script>

<template>
  <div
    class="flex h-full bg-white dark:bg-zinc-950 text-zinc-800 dark:text-zinc-200 overflow-hidden"
  >
    <div class="w-40 shrink-0 flex flex-col">
      <div class="flex-1 min-h-0">
        <FileTree
          :nodes="tree"
          :selectedFile="selectedFile"
          :changedFiles="changedFiles"
          :isLoading="isLoadingFiles"
          @select="selectFile"
        />
      </div>
      <ChangedFilesSummary
        :files="files"
        :originalFiles="originalFiles"
        :changedFiles="changedFiles"
        @selectFile="selectFile"
      />
    </div>

    <CodePanel
      :selectedFile="selectedFile"
      :currentContent="currentContent"
      :originalContent="originalContent"
      :isChanged="isChanged"
      :viewMode="viewMode"
      :isConnectingToSandbox="!threadId || isLoadingFiles"
      @viewModeChange="viewMode = $event"
    />

    <div class="w-64 shrink-0">
      <ChatPanel
        :messages="visibleMessages"
        :isLoading="stream.isLoading.value"
        :error="visibleError"
        :showNewThread="showNewThread"
        @submit="handleSubmit"
        @newThread="handleNewThread"
      />
    </div>
  </div>
</template>
