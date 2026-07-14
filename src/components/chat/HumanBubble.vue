<script setup lang="ts"></script>

<template>
  <div class="flex justify-end items-end gap-2" data-testid="sdk-preview-chat-turn">
    <div
      class="max-w-[80%] rounded-xl rounded-br-sm bg-primary-dark text-white px-4 py-3 text-sm leading-relaxed"
    >
      <slot />
    </div>
    <div
      class="shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-surface-tertiary border border-border"
    >
      <svg class="w-4 h-4" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 4L16 28L30 4H24.5L16 18.5L7.5 4H2Z" fill="#41B883" />
        <path d="M7.5 4L16 18.5L24.5 4H19.5L16.0653 10.0126L12.5 4H7.5Z" fill="#35495E" />
      </svg>
    </div>
  </div>
</template>
