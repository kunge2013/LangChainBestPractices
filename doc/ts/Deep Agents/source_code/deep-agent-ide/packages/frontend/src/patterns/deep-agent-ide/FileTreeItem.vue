<script setup lang="ts">
import { ref } from "vue";
import type { FileTreeNode } from "./types";
import FileIcon from "./FileIcon.vue";

const props = defineProps<{
  node: FileTreeNode;
  depth: number;
  selectedFile: string | null;
  changedFiles: Set<string>;
}>();

const emit = defineEmits<{
  select: [path: string];
}>();

const isOpen = ref(props.depth < 2);

function handleClick() {
  if (props.node.type === "directory") {
    isOpen.value = !isOpen.value;
  } else {
    emit("select", props.node.path);
  }
}
</script>

<template>
  <div>
    <button
      type="button"
      @click="handleClick"
      :class="[
        'w-full text-left flex items-center gap-1.5 px-2 py-1 text-xs font-mono hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer rounded',
        node.path === selectedFile
          ? 'bg-black/10 dark:bg-white/10 text-blue-500 dark:text-blue-400'
          : 'text-zinc-700 dark:text-zinc-300',
      ]"
      :style="{ paddingLeft: `${depth * 14 + 8}px` }"
    >
      <span
        v-if="node.type === 'directory'"
        :class="[
          'text-[10px] text-zinc-400 dark:text-zinc-500 transition-transform',
          isOpen ? 'rotate-90' : '',
        ]"
      >
        ▶
      </span>
      <FileIcon
        :name="node.name"
        :type="node.type"
        :isOpen="node.type === 'directory' ? isOpen : undefined"
        :size="16"
      />
      <span class="truncate">{{ node.name }}</span>
      <span
        v-if="changedFiles.has(node.path)"
        class="ml-auto w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0"
        title="Modified"
      />
    </button>

    <div v-if="node.type === 'directory' && isOpen && node.children">
      <FileTreeItem
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        :selectedFile="selectedFile"
        :changedFiles="changedFiles"
        @select="emit('select', $event)"
      />
    </div>
  </div>
</template>
