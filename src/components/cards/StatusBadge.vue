<script setup lang="ts">
const props = defineProps<{
  status: "pending" | "running" | "complete" | "error";
  label?: string;
}>();

const config = {
  pending: { color: "var(--color-text-tertiary)", icon: "○", label: "Pending" },
  running: { color: "var(--color-warning)", icon: "◉", label: "Running" },
  complete: { color: "var(--color-success)", icon: "✓", label: "Complete" },
  error: { color: "var(--color-error)", icon: "✕", label: "Error" },
} as const;
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 text-xs font-medium"
    :style="{ color: config[props.status].color }"
  >
    <span :class="props.status === 'running' ? 'animate-pulse' : ''">{{
      config[props.status].icon
    }}</span>
    {{ props.label ?? config[props.status].label }}
  </span>
</template>
