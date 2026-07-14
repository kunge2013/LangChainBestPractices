<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    data: unknown;
    maxHeight?: number;
  }>(),
  { maxHeight: 200 },
);

const json = computed(() =>
  typeof props.data === "string" ? props.data : JSON.stringify(props.data, null, 2),
);
</script>

<template>
  <pre
    class="overflow-auto rounded-md bg-surface-tertiary px-3 py-2 text-xs font-mono text-text-secondary leading-relaxed"
    :style="{ maxHeight: `${maxHeight}px` }"
    >{{ json }}</pre
  >
</template>
