import { afterEach, describe, expect, test } from "bun:test";

import {
  LocalSandboxNotAllowedError,
  RemoteSandboxUnavailableError,
  assertLocalSandboxAllowed,
  createLocalShellBackendOptions,
  getLocalSandboxEnv,
  handleRemoteSandboxAuthFailure,
  isDevelopmentEnvironment,
  resolveSandboxBackendMode,
} from "./sandbox-security.js";

const ENV_KEYS = [
  "NODE_ENV",
  "SANDBOX_BACKEND",
  "PATH",
  "HOME",
  "LANGSMITH_API_KEY",
  "ANTHROPIC_API_KEY",
] as const;

const savedEnv: Partial<Record<(typeof ENV_KEYS)[number], string | undefined>> = {};

afterEach(() => {
  for (const key of ENV_KEYS) {
    const value = savedEnv[key];
    if (value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = value;
    }
  }
});

function snapshotEnv(): void {
  for (const key of ENV_KEYS) {
    savedEnv[key] = process.env[key];
  }
}

describe("isDevelopmentEnvironment", () => {
  test("returns true only when NODE_ENV is development", () => {
    snapshotEnv();
    process.env.NODE_ENV = "development";
    expect(isDevelopmentEnvironment()).toBe(true);

    process.env.NODE_ENV = "production";
    expect(isDevelopmentEnvironment()).toBe(false);
  });
});

describe("resolveSandboxBackendMode", () => {
  test("allows local mode in development", () => {
    snapshotEnv();
    process.env.NODE_ENV = "development";
    process.env.SANDBOX_BACKEND = "local";
    expect(resolveSandboxBackendMode()).toBe("local");
  });

  test("rejects SANDBOX_BACKEND=local outside development", () => {
    snapshotEnv();
    process.env.NODE_ENV = "production";
    process.env.SANDBOX_BACKEND = "local";
    expect(() => resolveSandboxBackendMode()).toThrow(LocalSandboxNotAllowedError);
  });

  test("passes through langsmith mode in production", () => {
    snapshotEnv();
    process.env.NODE_ENV = "production";
    process.env.SANDBOX_BACKEND = "langsmith";
    expect(resolveSandboxBackendMode()).toBe("langsmith");
  });
});

describe("assertLocalSandboxAllowed", () => {
  test("throws outside development", () => {
    snapshotEnv();
    process.env.NODE_ENV = "production";
    expect(() => assertLocalSandboxAllowed("test")).toThrow(LocalSandboxNotAllowedError);
  });

  test("allows development", () => {
    snapshotEnv();
    process.env.NODE_ENV = "development";
    expect(() => assertLocalSandboxAllowed("test")).not.toThrow();
  });
});

describe("handleRemoteSandboxAuthFailure", () => {
  test("returns false in development", () => {
    snapshotEnv();
    process.env.NODE_ENV = "development";
    expect(handleRemoteSandboxAuthFailure()).toBe(false);
  });

  test("throws in production", () => {
    snapshotEnv();
    process.env.NODE_ENV = "production";
    expect(() => handleRemoteSandboxAuthFailure()).toThrow(RemoteSandboxUnavailableError);
  });
});

describe("getLocalSandboxEnv", () => {
  test("does not inherit server secrets", () => {
    snapshotEnv();
    process.env.LANGSMITH_API_KEY = "ls-secret";
    process.env.ANTHROPIC_API_KEY = "anthropic-secret";
    process.env.PATH = "/usr/bin";

    const env = getLocalSandboxEnv();

    expect(env.PATH).toBe("/usr/bin");
    expect(env.LANGSMITH_API_KEY).toBeUndefined();
    expect(env.ANTHROPIC_API_KEY).toBeUndefined();
    expect(env.NODE_ENV).toBe("development");
  });
});

describe("createLocalShellBackendOptions", () => {
  test("disables environment inheritance", () => {
    const options = createLocalShellBackendOptions({
      rootDir: "/tmp/sandbox",
      virtualMode: true,
    });

    expect(options.inheritEnv).toBe(false);
    expect(options.env).toEqual(getLocalSandboxEnv());
  });
});
