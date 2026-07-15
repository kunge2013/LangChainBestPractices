import type { Context, Hono } from "hono";
import type { SandboxBackendProtocolV2 } from "deepagents";

import { getOrCreateSandboxForThread } from "./utils.js";

const SANDBOX_BASE_DIR = "/app";
const SAFE_PATH_RE = /^\/app(\/[\w.-]+)*$/;
const THREAD_ID_RE = /^[a-zA-Z0-9_-]{1,128}$/;

function normalizePath(raw: string): string {
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    decoded = raw;
  }

  const segments = decoded.split("/");
  const resolved: string[] = [];
  for (const seg of segments) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") {
      resolved.pop();
    } else {
      resolved.push(seg);
    }
  }
  return "/" + resolved.join("/");
}

function getValidatedPath(c: Context, fallback?: string): string | Response {
  const raw = (c.req.query("filePath") ?? fallback ?? "").trim();
  if (!raw) {
    return c.json({ error: "filePath query parameter is required" }, 400);
  }
  const normalized = normalizePath(raw);
  if (!normalized.startsWith(SANDBOX_BASE_DIR) || !SAFE_PATH_RE.test(normalized)) {
    return c.json(
      {
        error: `Path must be under ${SANDBOX_BASE_DIR} and contain only valid characters`,
        received: raw,
        normalized,
      },
      400,
    );
  }
  return normalized;
}

function getThreadId(c: Context): string | Response {
  const threadId = c.req.param("threadId");
  if (!threadId) {
    return c.json({ error: "threadId path parameter is required" }, 400);
  }
  if (!THREAD_ID_RE.test(threadId)) {
    return c.json({ error: "Invalid threadId format" }, 400);
  }
  return threadId;
}

async function getThreadSandbox(c: Context) {
  const threadId = getThreadId(c);
  if (threadId instanceof Response) return { error: threadId };

  const sandbox = await getOrCreateSandboxForThread(threadId);
  return { sandbox, threadId, sandboxId: sandbox.id };
}

interface FileEntry {
  name: string;
  type: "file" | "directory";
  path: string;
  size: number;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function sortEntries(entries: FileEntry[]): FileEntry[] {
  return [...entries].sort((a, b) => a.path.localeCompare(b.path));
}

type FileInfoLike = {
  path: string;
  is_dir?: boolean;
  size?: number;
};

type ListingSandbox = SandboxBackendProtocolV2 & {
  glob?: (pattern: string, searchPath?: string) => Promise<{ files?: FileInfoLike[]; error?: string | null }>;
  ls?: (dirPath: string) => Promise<{ files?: FileInfoLike[]; error?: string | null }>;
};

function toAbsolutePath(rootPath: string, entryPath: string): string {
  const rootNorm = rootPath.replace(/\/$/, "") || rootPath;
  if (entryPath === rootNorm || entryPath.startsWith(`${rootNorm}/`)) return entryPath;
  if (entryPath.startsWith("/")) return `${rootNorm}${entryPath}`;
  return `${rootNorm}/${entryPath.replace(/^\//, "")}`;
}

function fileInfoToEntry(info: FileInfoLike, rootPath: string): FileEntry {
  const fullPath = toAbsolutePath(rootPath, info.path);
  return {
    name: fullPath.split("/").pop() || fullPath,
    type: info.is_dir ? "directory" : "file",
    path: fullPath,
    size: info.size ?? 0,
  };
}

async function listDirectoryEntries(
  sandbox: SandboxBackendProtocolV2,
  dirPath: string,
): Promise<FileEntry[]> {
  const listingSandbox = sandbox as ListingSandbox;
  if (typeof listingSandbox.ls !== "function") {
    throw new Error("Sandbox backend does not support ls()");
  }

  const result = await listingSandbox.ls(dirPath);
  if (result.error) throw new Error(result.error);

  return (result.files ?? [])
    .map((info) => fileInfoToEntry(info, dirPath))
    .filter((entry) => entry.path !== dirPath);
}

async function listTreeEntries(
  sandbox: SandboxBackendProtocolV2,
  rootPath: string,
): Promise<FileEntry[]> {
  const listingSandbox = sandbox as ListingSandbox;
  if (typeof listingSandbox.glob !== "function") {
    throw new Error("Sandbox backend does not support glob()");
  }

  const result = await listingSandbox.glob("**", rootPath);
  if (result.error) throw new Error(result.error);

  const entries = (result.files ?? []).map((info) => fileInfoToEntry(info, rootPath));
  const hasRoot = entries.some((entry) => entry.path === rootPath);
  if (!hasRoot) {
    entries.unshift({
      name: rootPath.split("/").pop() || rootPath,
      type: "directory",
      path: rootPath,
      size: 0,
    });
  }
  return entries;
}

// [AGC:START] tool=Cc author=fangkun
export function registerSandbox(app: Hono) {
  app.get("/sandbox/:threadId/ls", async (c) => {
    const dirPath = getValidatedPath(c, "/app");
    if (dirPath instanceof Response) return dirPath;

    try {
      const result = await getThreadSandbox(c);
      if ("error" in result) return result.error;

      const entries = await listDirectoryEntries(result.sandbox, dirPath);

      return c.json({
        path: dirPath,
        entries: sortEntries(entries),
      });
    } catch (error) {
      return c.json({ error: getErrorMessage(error), path: dirPath }, 500);
    }
  });

  app.get("/sandbox/:threadId/tree", async (c) => {
    const rootPath = getValidatedPath(c, "/app");
    if (rootPath instanceof Response) return rootPath;

    try {
      const result = await getThreadSandbox(c);
      if ("error" in result) return result.error;

      const entries = await listTreeEntries(result.sandbox, rootPath);

      return c.json({
        path: rootPath,
        entries: sortEntries(entries),
        sandboxId: result.sandboxId,
      });
    } catch (error) {
      return c.json({ error: getErrorMessage(error), path: rootPath }, 500);
    }
  });

  app.get("/sandbox/:threadId/file", async (c) => {
    const filePath = getValidatedPath(c);
    if (filePath instanceof Response) return filePath;

    const result = await getThreadSandbox(c);
    if ("error" in result) return result.error;

    try {
      if (!result.sandbox.downloadFiles) {
        return c.json({ error: "downloadFiles is not supported" }, 500);
      }
      const results = await result.sandbox.downloadFiles([filePath]);
      const file = results[0];

      if (file.error) {
        return c.json({ error: file.error, path: filePath }, 404);
      }

      const content = new TextDecoder().decode(file.content!);
      return c.json({ path: filePath, content });
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      return c.json({ error: message, path: filePath }, 500);
    }
  });

  app.get("/sandbox/:threadId/info", async (c) => {
    const threadId = getThreadId(c);
    if (threadId instanceof Response) return threadId;

    try {
      const sandbox = await getOrCreateSandboxForThread(threadId);
      const isRunning =
        "isRunning" in sandbox &&
        typeof (sandbox as { isRunning?: boolean }).isRunning === "boolean"
          ? (sandbox as { isRunning: boolean }).isRunning
          : true;
      return c.json({
        threadId,
        sandboxId: sandbox.id,
        isRunning,
      });
    } catch (error) {
      return c.json({ error: getErrorMessage(error), threadId }, 500);
    }
  });
}
// [AGC:END]
