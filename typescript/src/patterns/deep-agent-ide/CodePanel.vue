<script setup lang="ts">
// [AGC:START] tool=Cc author=fangkun
import { computed, ref, watchEffect, onMounted, onUnmounted } from "vue";
import { DiffView, DiffModeEnum } from "@git-diff-view/vue";
import { generateDiffFile } from "@git-diff-view/file";
import "@git-diff-view/vue/styles/diff-view.css";
import FileIcon from "./FileIcon.vue";

const props = defineProps<{
  selectedFile: string | null;
  currentContent: string | undefined;
  originalContent: string | undefined;
  isChanged: boolean;
  viewMode: "code" | "diff";
  isConnectingToSandbox: boolean;
}>();

const emit = defineEmits<{
  viewModeChange: [mode: "code" | "diff"];
}>();

function baseName(path: string): string {
  return path.split("/").pop() || path;
}

const LANG_MAP: Record<string, string> = {
  ts: "typescript",
  tsx: "tsx",
  js: "javascript",
  jsx: "jsx",
  json: "json",
  md: "markdown",
  css: "css",
  html: "html",
  py: "python",
  sh: "bash",
  yml: "yaml",
  yaml: "yaml",
};

function getLang(filename: string): string {
  const ext = filename.split(".")?.pop()?.toLowerCase() || "";
  return LANG_MAP[ext] || "text";
}

function getDiffLang(filename: string): string {
  const ext = filename.split(".")?.pop()?.toLowerCase() || "";
  return LANG_MAP[ext] || "plaintext";
}

let highlighterPromise: Promise<import("shiki").Highlighter> | null = null;
function getHighlighter() {
  if (!highlighterPromise) {
    highlighterPromise = import("shiki").then((shiki) =>
      shiki.createHighlighter({
        themes: ["github-dark", "github-light"],
        langs: [
          "javascript",
          "typescript",
          "json",
          "markdown",
          "css",
          "html",
          "python",
          "bash",
          "yaml",
          "tsx",
          "jsx",
        ],
      }),
    );
  }
  return highlighterPromise;
}

function computeIsDarkMode(): boolean {
  const root = document.documentElement;
  if (root.classList.contains("dark")) return true;
  if (root.classList.contains("light")) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function useIsDark() {
  const isDark = ref(computeIsDarkMode());
  let observer: MutationObserver | null = null;
  let mqRemove: (() => void) | null = null;

  onMounted(() => {
    observer = new MutationObserver(() => {
      isDark.value = computeIsDarkMode();
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onMq = () => {
      isDark.value = computeIsDarkMode();
    };
    mq.addEventListener("change", onMq);
    mqRemove = () => mq.removeEventListener("change", onMq);
  });

  onUnmounted(() => {
    mqRemove?.();
    observer?.disconnect();
  });

  return isDark;
}

const isDark = useIsDark();

const name = computed(() => (props.selectedFile ? baseName(props.selectedFile) : ""));

const diffFile = computed(() => {
  if (
    !props.isChanged ||
    !props.selectedFile ||
    props.originalContent === undefined ||
    props.currentContent === undefined
  ) {
    return null;
  }
  try {
    const fileName = baseName(props.selectedFile);
    const lang = getDiffLang(fileName);
    const file = generateDiffFile(
      fileName,
      props.originalContent || "",
      fileName,
      props.currentContent || "",
      lang,
      lang,
    );
    file.initTheme(isDark.value ? "dark" : "light");
    file.init();
    file.buildSplitDiffLines();
    file.buildUnifiedDiffLines();
    return file;
  } catch {
    return null;
  }
});

const diffViewTheme = computed(() => (isDark.value ? "dark" : "light"));
const showDiffTab = computed(() => props.isChanged && diffFile.value);
const effectiveMode = computed(() =>
  showDiffTab.value && props.viewMode === "diff" ? "diff" : "code",
);

const highlightedHtml = ref("");

watchEffect(() => {
  const content = props.currentContent;
  const file = props.selectedFile;
  const mode = effectiveMode.value;

  if (mode !== "code" || content === undefined || !file) {
    highlightedHtml.value = "";
    return;
  }

  const lang = getLang(baseName(file));
  const shikiTheme = isDark.value ? "github-dark" : "github-light";
  getHighlighter()
    .then((hl) => {
      const loaded = hl.getLoadedLanguages();
      const html = hl.codeToHtml(content, {
        lang: loaded.includes(lang) ? lang : "text",
        theme: shikiTheme,
        transformers: [
          {
            line(node, line) {
              node.children.unshift({
                type: "element",
                tagName: "span",
                properties: { class: "line-number" },
                children: [{ type: "text", value: String(line) }],
              });
            },
          },
        ],
      });
      highlightedHtml.value = html;
    })
    .catch(() => {
      highlightedHtml.value = "";
    });
});
// [AGC:END]
</script>

<template>
  <div
    v-if="!selectedFile"
    class="flex-1 flex items-center justify-center bg-white dark:bg-zinc-950 text-sm px-6"
  >
    <template v-if="isConnectingToSandbox">
      <div class="flex flex-col items-center gap-2 text-center max-w-sm">
        <p class="text-zinc-500 dark:text-zinc-400">Connecting you to the sandbox…</p>
        <p class="text-zinc-400 dark:text-zinc-600 text-xs">
          Negotiating with grains of sand so they agree to look like files.
        </p>
      </div>
    </template>
    <span v-else class="text-zinc-400 dark:text-zinc-500">Select a file to view its contents</span>
  </div>
  <div v-else class="flex-1 flex flex-col bg-white dark:bg-zinc-950 min-w-0">
    <div
      class="flex items-center border-b border-zinc-200 dark:border-zinc-700/50 bg-zinc-50 dark:bg-zinc-900 pt-px"
    >
      <div class="flex items-center gap-1 px-1">
        <button
          type="button"
          @click="emit('viewModeChange', 'code')"
          :class="[
            'px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5',
            effectiveMode === 'code'
              ? 'text-zinc-800 dark:text-zinc-200 border-b-2 border-blue-500 dark:border-blue-400'
              : 'text-zinc-400 dark:text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300',
          ]"
        >
          <FileIcon :name="name" type="file" :size="14" />
          {{ name }}
        </button>
        <button
          v-if="showDiffTab"
          type="button"
          @click="emit('viewModeChange', 'diff')"
          :class="[
            'px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5',
            effectiveMode === 'diff'
              ? 'text-zinc-800 dark:text-zinc-200 border-b-2 border-amber-500 dark:border-amber-400'
              : 'text-zinc-400 dark:text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300',
          ]"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-amber-500 dark:bg-amber-400" />
          Diff
        </button>
      </div>

      <div
        v-if="isChanged"
        class="ml-auto px-3 text-[10px] font-medium text-amber-500 dark:text-amber-400 uppercase tracking-wider"
      >
        Modified
      </div>
    </div>

    <div class="flex-1 overflow-auto min-h-0 bg-white dark:bg-[#24292e]">
      <DiffView
        v-if="effectiveMode === 'diff' && diffFile"
        :diffFile="diffFile"
        :diffViewMode="DiffModeEnum.Unified"
        :diffViewTheme="diffViewTheme"
        :diffViewFontSize="12"
        :diffViewHighlight="true"
        class="w-full"
      />
      <div v-else-if="highlightedHtml" class="shiki-container" v-html="highlightedHtml" />
      <pre
        v-else-if="currentContent !== undefined"
        class="p-4 text-xs font-mono text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap break-all leading-relaxed"
        >{{ currentContent }}</pre
      >
      <div
        v-else
        class="flex items-center justify-center h-full text-zinc-400 dark:text-zinc-500 text-sm"
      >
        Loading file…
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.shiki-container pre) {
  margin: 0;
  padding: 16px 16px 16px 0;
  background: transparent !important;
  font-size: 12px;
  line-height: 1.6;
}
:deep(.shiki-container code) {
  font-family: "Menlo", "Consolas", monospace;
}
:deep(.shiki-container .line) {
  display: inline-block;
  width: 100%;
}
:deep(.shiki-container .line-number) {
  display: inline-block;
  width: 40px;
  text-align: right;
  padding-right: 16px;
  margin-right: 12px;
  color: #afb8c1;
  user-select: none;
  border-right: 1px solid #d0d7de;
}
:global(.dark) :deep(.shiki-container .line-number) {
  color: #6e7681;
  border-right-color: #30363d;
}
</style>