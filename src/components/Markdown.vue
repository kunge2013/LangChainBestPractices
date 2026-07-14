<script setup lang="ts">
import { computed } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

const props = defineProps<{
  content?: string;
  class?: string;
}>();

marked.setOptions({ gfm: true, breaks: true });

const html = computed(() => {
  const text = props.content ?? "";
  if (!text) return "";
  const raw = marked.parse(text) as string;
  return DOMPurify.sanitize(raw);
});
</script>

<template>
  <div :class="['markdown-content', $props.class]" v-html="html" />
</template>
