<script setup lang="ts">
import { computed } from "vue";
import { resolveFileIconSvg } from "./file-icon";

const props = withDefaults(
  defineProps<{
    name: string;
    type: "file" | "directory";
    isOpen?: boolean;
    size?: number;
  }>(),
  { size: 16 },
);

const icon = computed(() => resolveFileIconSvg(props.name, props.type, props.isOpen));
</script>

<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="props.size"
    :height="props.size"
    :viewBox="icon.viewBox"
    v-html="icon.body"
    class="shrink-0"
  />
</template>
