<script setup lang="ts">
defineProps<{
  slugs: string[];
  frameworkLabel: string;
}>();

const emit = defineEmits<{
  select: [slug: string];
}>();

function formatPatternLabel(slug: string): string {
  return slug
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
</script>

<template>
  <div class="min-h-[400px] p-6">
    <div class="mx-auto max-w-3xl">
      <h1 class="text-lg font-semibold text-[var(--color-text)]">{{ frameworkLabel }} examples</h1>
      <p class="mt-1 text-sm text-[var(--color-text-tertiary)]">
        Choose a pattern to preview in this sandbox.
      </p>
      <ul class="mt-6 grid gap-2 sm:grid-cols-2">
        <li v-for="slug in slugs" :key="slug">
          <button
            type="button"
            :title="`${formatPatternLabel(slug)} (${slug})`"
            class="flex w-full min-w-0 cursor-pointer items-center gap-3 overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-secondary)] px-4 py-3 text-left text-sm whitespace-nowrap text-[var(--color-text)] transition-colors hover:border-[var(--color-primary)] hover:text-[var(--color-primary)]"
            @click="emit('select', slug)"
          >
            <span class="min-w-0 flex-1 truncate font-medium">{{ formatPatternLabel(slug) }}</span>
            <span
              class="max-w-[45%] shrink-0 truncate font-mono text-xs text-[var(--color-text-tertiary)]"
            >
              {{ slug }}
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
