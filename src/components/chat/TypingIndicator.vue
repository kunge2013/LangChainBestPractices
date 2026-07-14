<script setup lang="ts"></script>

<template>
  <div class="flex justify-start" data-testid="sdk-preview-chat-turn">
    <div class="bg-surface-secondary border border-border rounded-xl rounded-bl-sm px-4 py-3">
      <div class="flex gap-1.5">
        <span
          v-for="i in [0, 1, 2]"
          :key="i"
          class="w-2 h-2 rounded-full bg-primary animate-bounce"
          :style="{ animationDelay: `${i * 150}ms` }"
        />
      </div>
    </div>
  </div>
</template>
