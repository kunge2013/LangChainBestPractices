<script setup lang="ts">
import { ref, inject } from "vue";

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    placeholder?: string;
    showNewThread?: boolean;
  }>(),
  {
    disabled: false,
    placeholder: "Type a message...",
    showNewThread: false,
  },
);

const emit = defineEmits<{
  submit: [text: string];
  newThread: [];
}>();

const text = ref("");

function handleSubmit() {
  const trimmed = text.value.trim();
  if (!trimmed || props.disabled) return;
  emit("submit", trimmed);
  text.value = "";
}

function handleNewThread() {
  emit("newThread");
}
</script>

<template>
  <div class="space-y-2">
    <form @submit.prevent="handleSubmit" class="flex gap-2">
      <input
        v-model="text"
        type="text"
        :placeholder="placeholder"
        :disabled="disabled"
        class="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary disabled:opacity-50"
      />
      <button
        type="submit"
        :disabled="disabled || !text.trim()"
        class="rounded-lg bg-primary-dark px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40 transition-opacity"
      >
        Send
      </button>
    </form>
    <button
      v-if="showNewThread"
      type="button"
      @click="handleNewThread"
      class="rounded-lg border border-border bg-surface-secondary px-3 py-1.5 text-xs text-text-secondary hover:border-primary hover:text-primary transition-colors cursor-pointer"
    >
      + New thread
    </button>
  </div>
</template>
