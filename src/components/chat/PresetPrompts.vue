<script setup lang="ts">

defineProps<{
  prompts: string[];
  disabled?: boolean;
}>();

const emit = defineEmits<{
  select: [prompt: string];
}>();

function handleSelect(prompt: string) {
  emit("select", prompt);
}
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 px-4 py-3">
    <div class="text-xs text-text-secondary font-medium">Try these prompts:</div>
    <button
      v-for="prompt in prompts"
      :key="prompt"
      type="button"
      @click="handleSelect(prompt)"
      :disabled="disabled"
      class="rounded-lg border border-border bg-surface-secondary px-3 py-1.5 text-xs text-text-secondary hover:border-primary hover:text-primary disabled:opacity-40 transition-colors cursor-pointer"
    >
      {{ prompt }}
    </button>
  </div>
</template>
