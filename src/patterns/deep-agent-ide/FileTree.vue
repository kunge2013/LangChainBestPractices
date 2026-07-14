<script setup lang="ts">
// [AGC:START] tool=Cc author=fangkun
import type { FileTreeNode } from "./types";
import FileTreeItem from "./FileTreeItem.vue";

defineProps<{
  nodes: FileTreeNode[];
  selectedFile: string | null;
  changedFiles: Set<string>;
  isLoading?: boolean;
}>();

const emit = defineEmits<{
  select: [path: string];
}>();
// [AGC:END]
</script>

<template>
  <div
    class="flex flex-col h-full bg-zinc-50 dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-700/50"
  >
    <div
      class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 border-b border-zinc-200 dark:border-zinc-700/50"
    >
      Explorer
    </div>
    <div class="flex-1 overflow-y-auto py-1">
      <div v-if="isLoading" class="flex items-center justify-center py-8">
        <div
          class="animate-spin w-4 h-4 border-2 border-zinc-300 dark:border-zinc-600 border-t-zinc-600 dark:border-t-zinc-300 rounded-full"
        />
      </div>
      <div
        v-else-if="nodes.length === 0"
        class="px-3 py-4 text-xs text-zinc-400 dark:text-zinc-500 text-center"
      >
        No files
      </div>
      <template v-else>
        <FileTreeItem
          v-for="node in nodes"
          :key="node.path"
          :node="node"
          :depth="0"
          :selectedFile="selectedFile"
          :changedFiles="changedFiles"
          @select="emit('select', $event)"
        />
      </template>
    </div>
  </div>
</template>