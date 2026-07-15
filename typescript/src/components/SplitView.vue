<script setup lang="ts">
defineProps<{
  sidebarWidth?: number;
}>();
</script>

<template>
  <div class="split-view">
    <div class="split-main">
      <slot name="main" />
    </div>
    <div
      class="split-sidebar"
      :style="{ width: `${sidebarWidth ?? 280}px` }"
    >
      <slot name="sidebar" />
    </div>
  </div>
</template>

<style scoped>
.split-view {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.split-main {
  flex: 1;
  min-width: 0;
  overflow: auto;
}

.split-sidebar {
  flex-shrink: 0;
  overflow-y: auto;
  border-left: 1px solid var(--border, #e5e7eb);
}
</style>
