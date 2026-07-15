import type { LocalShellBackendOptions } from "deepagents";

export function isDevelopmentEnvironment(): boolean {
  return process.env.NODE_ENV === "development";
}

export class LocalSandboxNotAllowedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "LocalSandboxNotAllowedError";
  }
}

export class RemoteSandboxUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RemoteSandboxUnavailableError";
  }
}

/**
 * Resolve `SANDBOX_BACKEND`. `local` is only honored in development; production
 * callers must use remote LangSmith sandboxes.
 */
export function resolveSandboxBackendMode(): "local" | "langsmith" | "auto" {
  const raw = process.env.SANDBOX_BACKEND?.trim().toLowerCase();
  if (raw === "local") {
    if (!isDevelopmentEnvironment()) {
      throw new LocalSandboxNotAllowedError(
        "SANDBOX_BACKEND=local is only supported when NODE_ENV=development.",
      );
    }
    return "local";
  }
  if (raw === "langsmith") return "langsmith";
  return "auto";
}

export function assertLocalSandboxAllowed(context: string): void {
  if (!isDevelopmentEnvironment()) {
    throw new LocalSandboxNotAllowedError(
      `Local sandbox is disabled outside development (${context}). ` +
        "Use a sandbox-enabled LANGSMITH_API_KEY or set SANDBOX_BACKEND=langsmith.",
    );
  }
}

export function handleRemoteSandboxAuthFailure(): false {
  if (isDevelopmentEnvironment()) {
    console.warn(
      "[sandbox] LangSmith Sandbox API returned 403; falling back to LocalShellBackend in development. " +
        "Set SANDBOX_BACKEND=langsmith to require remote sandboxes, or use a sandbox-enabled LANGSMITH_API_KEY.",
    );
    return false;
  }

  throw new RemoteSandboxUnavailableError(
    "LangSmith Sandbox API returned 403. Remote sandboxes are required outside development. " +
      "Use a sandbox-enabled LANGSMITH_API_KEY.",
  );
}

const LOCAL_SANDBOX_ENV_ALLOWLIST = [
  "PATH",
  "HOME",
  "USER",
  "LANG",
  "LC_ALL",
  "TMPDIR",
  "TEMP",
  "TMP",
] as const;

/** Minimal environment for local dev sandboxes — never inherit server secrets. */
export function getLocalSandboxEnv(): Record<string, string> {
  const env: Record<string, string> = {};
  for (const key of LOCAL_SANDBOX_ENV_ALLOWLIST) {
    const value = process.env[key];
    if (value) env[key] = value;
  }

  if (!env.PATH) {
    env.PATH = "/usr/local/bin:/usr/bin:/bin";
  }
  if (!env.HOME) {
    env.HOME = "/tmp";
  }
  env.NODE_ENV = "development";

  return env;
}

export function createLocalShellBackendOptions(
  options: Pick<LocalShellBackendOptions, "rootDir" | "virtualMode" | "initialFiles">,
): LocalShellBackendOptions {
  return {
    ...options,
    inheritEnv: false,
    env: getLocalSandboxEnv(),
  };
}
