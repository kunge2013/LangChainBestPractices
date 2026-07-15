import { ref, watch, type Ref } from "vue";
import { AGENT_SERVER_URL } from "@/constants";
import type { FileEntry, FileSnapshot, FileTreeNode } from "./types";

function buildTree(entries: FileEntry[], rootPath: string): FileTreeNode[] {
  const root: FileTreeNode[] = [];
  const dirMap = new Map<string, FileTreeNode>();

  const sorted = [...entries].sort((a, b) => {
    if (a.type !== b.type) return a.type === "directory" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  for (const entry of sorted) {
    const node: FileTreeNode = { ...entry, children: entry.type === "directory" ? [] : undefined };
    const parentPath = entry.path.substring(0, entry.path.lastIndexOf("/"));

    if (parentPath === rootPath || parentPath === "") {
      root.push(node);
    } else {
      const parent = dirMap.get(parentPath);
      if (parent?.children) parent.children.push(node);
      else root.push(node);
    }

    if (entry.type === "directory") {
      dirMap.set(entry.path, node);
    }
  }

  return root;
}

export function useSandboxFiles(threadIdRef: Ref<string | null>) {
  const tree = ref<FileTreeNode[]>([]);
  const files = ref<FileSnapshot>({});
  const originalFiles = ref<FileSnapshot>({});
  const selectedFile = ref<string | null>(null);
  const isLoadingFiles = ref(false);
  const changedFiles = ref<Set<string>>(new Set());
  const sandboxId = ref<string | null>(null);
  let initialLoadDone = false;
  let lastLoadedSandboxId: string | null = null;

  function setSelectedFile(path: string | null) {
    selectedFile.value = path;
  }

  async function fetchTree(): Promise<{
    entries: FileEntry[];
    sandboxId: string | null;
  }> {
    const tid = threadIdRef.value;
    if (!tid) return { entries: [], sandboxId: null };
    try {
      const res = await fetch(
        `${AGENT_SERVER_URL}/sandbox/${encodeURIComponent(tid)}/tree?filePath=/app`,
      );
      const data = await res.json();
      if (!res.ok || !Array.isArray(data.entries)) {
        console.error("Failed to fetch file tree:", data);
        return { entries: [], sandboxId: null };
      }
      const resolvedSandboxId = typeof data.sandboxId === "string" ? data.sandboxId : null;
      if (resolvedSandboxId) {
        sandboxId.value = resolvedSandboxId;
      }
      const entries: FileEntry[] = data.entries.filter(
        (e: FileEntry) => e.path !== "/app" && !e.path.includes("node_modules"),
      );
      tree.value = buildTree(entries, "/app");
      return { entries, sandboxId: resolvedSandboxId };
    } catch (e) {
      console.error("Failed to fetch file tree:", e);
      return { entries: [], sandboxId: null };
    }
  }

  async function fetchFileContent(path: string): Promise<string | null> {
    const tid = threadIdRef.value;
    if (!tid) return null;
    try {
      const res = await fetch(
        `${AGENT_SERVER_URL}/sandbox/${encodeURIComponent(tid)}/file?filePath=${encodeURIComponent(path)}`,
      );
      const data = await res.json();
      return data.content ?? null;
    } catch {
      return null;
    }
  }

  async function fetchAllFiles(entries: FileEntry[]): Promise<FileSnapshot> {
    const fileEntries = entries.filter((e) => e.type === "file");
    const snapshot: FileSnapshot = {};

    await Promise.all(
      fileEntries.map(async (entry) => {
        const content = await fetchFileContent(entry.path);
        if (content !== null) snapshot[entry.path] = content;
      }),
    );

    return snapshot;
  }

  async function loadInitial() {
    if (initialLoadDone || !threadIdRef.value) return;
    isLoadingFiles.value = true;

    const { entries, sandboxId: fetchedSandboxId } = await fetchTree();
    if (fetchedSandboxId && fetchedSandboxId === lastLoadedSandboxId && lastLoadedSandboxId) {
      initialLoadDone = true;
      isLoadingFiles.value = false;
      return;
    }

    initialLoadDone = true;
    if (fetchedSandboxId) {
      lastLoadedSandboxId = fetchedSandboxId;
    }

    const snapshot = await fetchAllFiles(entries);

    files.value = snapshot;
    originalFiles.value = snapshot;
    isLoadingFiles.value = false;

    const firstFile = entries.find((e) => e.type === "file");
    if (firstFile) selectedFile.value = firstFile.path;
  }

  function takeSnapshot() {
    originalFiles.value = { ...files.value };
    changedFiles.value = new Set();
  }

  async function refreshFiles() {
    isLoadingFiles.value = true;
    const { entries } = await fetchTree();
    const snapshot = await fetchAllFiles(entries);

    const originals = originalFiles.value;
    const changed = new Set<string>();
    for (const [path, content] of Object.entries(snapshot)) {
      if (originals[path] !== content) changed.add(path);
    }
    for (const path of Object.keys(originals)) {
      if (!(path in snapshot)) changed.add(path);
    }

    files.value = snapshot;
    changedFiles.value = changed;
    isLoadingFiles.value = false;
  }

  async function refreshSingleFile(filePath: string) {
    const content = await fetchFileContent(filePath);
    if (content === null) return;

    files.value = { ...files.value, [filePath]: content };

    const original = originalFiles.value[filePath];
    const next = new Set(changedFiles.value);
    if (original !== content) next.add(filePath);
    else next.delete(filePath);
    changedFiles.value = next;
  }

  async function refreshTreeAndFiles() {
    const { entries } = await fetchTree();
    const snapshot = await fetchAllFiles(entries);

    const originals = originalFiles.value;
    const changed = new Set<string>();
    for (const [path, content] of Object.entries(snapshot)) {
      if (originals[path] !== content) changed.add(path);
    }
    for (const path of Object.keys(originals)) {
      if (!(path in snapshot)) changed.add(path);
    }

    files.value = snapshot;
    changedFiles.value = changed;
  }

  watch(
    threadIdRef,
    (tid) => {
      if (tid) {
        initialLoadDone = false;
        loadInitial();
      }
    },
    { immediate: true },
  );

  return {
    tree,
    files,
    originalFiles,
    selectedFile,
    setSelectedFile,
    isLoadingFiles,
    changedFiles,
    sandboxId,
    takeSnapshot,
    refreshFiles,
    refreshSingleFile,
    refreshTreeAndFiles,
    fetchFileContent,
  };
}
