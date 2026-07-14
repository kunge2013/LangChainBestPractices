<script setup lang="ts">
// [AGC:START] tool=Cc author=fangkun
import { ref } from "vue";
import DeepAgentSubagentCardsPreview from "./patterns/deep-agent-subagent-cards/Preview.vue";
import DeepAgentIdePreview from "./patterns/deep-agent-ide/Preview.vue";

interface Pattern {
  id: string;
  label: string;
}

const patterns: Pattern[] = [
  { id: "subagent-cards", label: "Subagent Cards" },
  { id: "deep-agent-ide", label: "IDE" },
];

const activePattern = ref<Pattern>(patterns[0]);
// [AGC:END]
</script>

<template>
  <div class="flex flex-col h-screen">
    <nav
      class="flex items-center gap-2 px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-surface dark:bg-zinc-900"
    >
      <button
        v-for="p in patterns"
        :key="p.id"
        type="button"
        :class="[
          'px-3 py-1 rounded text-sm transition-colors cursor-pointer',
          activePattern.id === p.id
            ? 'bg-primary/20 font-medium'
            : 'hover:bg-gray-100 dark:hover:bg-zinc-800',
        ]"
        @click="activePattern = p"
      >
        {{ p.label }}
      </button>
    </nav>
    <main class="flex-1 min-h-0">
      <DeepAgentSubagentCardsPreview v-if="activePattern.id === 'subagent-cards'" />
      <DeepAgentIdePreview v-else-if="activePattern.id === 'deep-agent-ide'" />
    </main>
  </div>
</template>