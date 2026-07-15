<script setup lang="ts">
import { ref, onUpdated } from "vue";

const props = defineProps<{
  class?: string;
  /** Fill remaining space inside a flex parent instead of using the full viewport height. */
  embedded?: boolean;
}>();

const scrollRef = ref<HTMLDivElement>();

onUpdated(() => {
  const el = scrollRef.value;
  if (el) el.scrollTop = el.scrollHeight;
});
</script>

<template>
  <div
    :class="[
      'flex flex-col bg-surface',
      props.embedded ? 'min-h-0 flex-1' : 'h-screen',
      props.class,
    ]"
  >
    <div
      ref="scrollRef"
      data-testid="sdk-preview-messages"
      class="min-h-0 flex-1 overflow-y-auto px-4 py-4 space-y-4"
    >
      <slot />
    </div>
    <div v-if="$slots.input" class="shrink-0 border-t border-border px-4 py-3">
      <slot name="input" />
    </div>
  </div>
</template>
