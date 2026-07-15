<script setup lang="ts">
import { computed } from "vue";

interface Todo {
  status: "pending" | "in_progress" | "completed";
  content: string;
}

const props = defineProps<{
  todos: Todo[];
}>();

const STATUS_ICONS: Record<string, string> = {
  pending: "○",
  in_progress: "◉",
  completed: "✓",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "var(--color-text-tertiary)",
  in_progress: "var(--color-warning)",
  completed: "var(--color-success)",
};

const completed = computed(() => props.todos.filter((t) => t.status === "completed").length);
const pct = computed(() =>
  props.todos.length ? Math.round((completed.value / props.todos.length) * 100) : 0,
);
</script>

<template>
  <div class="rounded-lg border border-border bg-surface-secondary p-3 space-y-3">
    <div class="flex items-center justify-between">
      <span class="text-xs font-medium text-text">Todo List</span>
      <span class="text-xs text-text-tertiary">{{ completed }}/{{ todos.length }}</span>
    </div>
    <div class="w-full h-1.5 rounded-full bg-surface-tertiary overflow-hidden">
      <div
        class="h-full rounded-full bg-success transition-all duration-500"
        :style="{ width: `${pct}%` }"
      />
    </div>
    <ul class="space-y-1.5">
      <li v-for="(todo, i) in todos" :key="i" class="flex items-start gap-2 text-sm">
        <span
          :style="{ color: STATUS_COLORS[todo.status] ?? STATUS_COLORS.pending }"
          :class="todo.status === 'in_progress' ? 'animate-pulse' : ''"
          >{{ STATUS_ICONS[todo.status] ?? STATUS_ICONS.pending }}</span
        >
        <span
          :class="todo.status === 'completed' ? 'line-through text-text-tertiary' : 'text-text'"
        >
          {{ todo.content }}
        </span>
      </li>
    </ul>
  </div>
</template>
