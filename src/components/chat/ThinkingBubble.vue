<script setup lang="ts">
defineProps<{
  content: string;
  isStreaming: boolean;
}>();
</script>

<template>
  <div class="flex justify-start items-end gap-2" data-testid="sdk-preview-chat-turn">
    <div
      class="shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-surface-tertiary border border-border text-primary"
    >
      <svg
        class="w-4 h-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <rect x="3" y="11" width="18" height="10" rx="2" />
        <circle cx="12" cy="5" r="2" />
        <path d="M12 7v4" />
        <line x1="8" y1="16" x2="8" y2="16" />
        <line x1="16" y1="16" x2="16" y2="16" />
      </svg>
    </div>
    <div
      class="max-w-[80%] rounded-xl rounded-bl-sm bg-surface-secondary border border-border px-4 py-2.5 text-sm"
    >
      <div class="flex items-center gap-1.5 mb-1.5 text-xs font-medium text-primary">
        <svg
          :class="['w-3.5 h-3.5', isStreaming ? 'animate-pulse' : '']"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            d="M12 3l1.912 5.813a2 2 0 0 0 1.275 1.275L21 12l-5.813 1.912a2 2 0 0 0-1.275 1.275L12 21l-1.912-5.813a2 2 0 0 0-1.275-1.275L3 12l5.813-1.912a2 2 0 0 0 1.275-1.275L12 3z"
          />
        </svg>
        <span>{{ isStreaming ? "Thinking…" : "Thought" }}</span>
        <span class="text-text-tertiary font-normal">· {{ content.length }} chars</span>
      </div>
      <pre class="whitespace-pre-wrap text-xs font-mono text-text-secondary leading-relaxed m-0">{{
        content
      }}</pre>
    </div>
  </div>
</template>
