<script setup lang="ts"></script>

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
      class="max-w-[80%] rounded-xl rounded-bl-sm bg-surface-secondary border border-border text-text px-4 py-3 text-sm leading-relaxed"
    >
      <slot />
    </div>
  </div>
</template>
