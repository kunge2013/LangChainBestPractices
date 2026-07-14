<script setup lang="ts">
// [AGC:START] tool=Cc author=fangkun
import { ref, computed } from "vue";
import type { FileSnapshot } from "./types";
import FileIcon from "./FileIcon.vue";

const props = defineProps<{
  files: FileSnapshot;
  originalFiles: FileSnapshot;
  changedFiles: Set<string>;
}>();

const emit = defineEmits<{
  selectFile: [path: string];
}>();

const isOpen = ref(true);

function computeStats(oldContent: string, newContent: string) {
  const oldLines = oldContent.split("\n");
  const newLines = newContent.split("\n");
  let additions = 0;
  let deletions = 0;
  const max = Math.max(oldLines.length, newLines.length);
  for (let i = 0; i < max; i++) {
    if (i >= oldLines.length) additions++;
    else if (i >= newLines.length) deletions++;
    else if (oldLines[i] !== newLines[i]) {
      additions++;
      deletions++;
    }
  }
  return { additions, deletions };
}

const fileStats = computed(() => {
  const stats: { path: string; name: string; additions: number; deletions: number }[] = [];

  for (const path of props.changedFiles) {
    const oldContent = props.originalFiles[path] ?? "";
    const newContent = props.files[path] ?? "";
    const name = path.replace(/^\/app\//, "");
    const { additions, deletions } = computeStats(oldContent, newContent);
    stats.push({ path, name, additions, deletions });
  }

  return stats.sort((a, b) => a.name.localeCompare(b.name));
});

const totalAdditions = computed(() => fileStats.value.reduce((sum, f) => sum + f.additions, 0));
const totalDeletions = computed(() => fileStats.value.reduce((sum, f) => sum + f.deletions, 0));
// [AGC:END]
</script>

<template>
  <div v-if="fileStats.length > 0" class="border-t border-zinc-200 dark:border-zinc-700/50">
    <button
      type="button"
      @click="isOpen = !isOpen"
      class="w-full flex items-center gap-2 px-3 py-2 text-xs text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors cursor-pointer"
    >
      <span
        :class="[
          'text-[10px] text-zinc-400 dark:text-zinc-500 transition-transform',
          isOpen ? 'rotate-90' : '',
        ]"
      >
        ▶
      </span>
      <span class="font-semibold">
        {{ fileStats.length }} File{{ fileStats.length !== 1 ? "s" : "" }} Changed
      </span>
      <span class="ml-auto flex items-center gap-1.5 text-[10px]">
        <span v-if="totalAdditions > 0" class="text-green-400">+{{ totalAdditions }}</span>
        <span v-if="totalDeletions > 0" class="text-red-400">-{{ totalDeletions }}</span>
      </span>
    </button>

    <div v-if="isOpen" class="pb-1">
      <button
        v-for="file in fileStats"
        :key="file.path"
        type="button"
        @click="emit('selectFile', file.path)"
        class="w-full flex items-center gap-2 px-3 py-1 text-xs text-zinc-500 dark:text-zinc-400 hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer"
      >
        <FileIcon :name="file.name.split('/').pop() || file.name" type="file" :size="16" />
        <span class="truncate text-zinc-700 dark:text-zinc-300 font-mono text-[11px]">{{
          file.name
        }}</span>
        <span class="ml-auto flex items-center gap-1.5 text-[10px] shrink-0">
          <span v-if="file.additions > 0" class="text-green-400">+{{ file.additions }}</span>
          <span v-if="file.deletions > 0" class="text-red-400">-{{ file.deletions }}</span>
        </span>
      </button>
    </div>
  </div>
</template>