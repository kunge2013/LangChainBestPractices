import iconData from "@iconify-json/vscode-icons/icons.json";

const icons = iconData.icons as Record<string, { body: string }>;
const defaultSize = iconData.width ?? 32;

const EXT_TO_ICON: Record<string, string> = {
  js: "file-type-js",
  mjs: "file-type-js",
  cjs: "file-type-js",
  jsx: "file-type-reactjs",
  ts: "file-type-typescript",
  mts: "file-type-typescript",
  cts: "file-type-typescript",
  tsx: "file-type-reactts",
  json: "file-type-json",
  md: "file-type-markdown",
  css: "file-type-css",
  scss: "file-type-scss",
  less: "file-type-less",
  html: "file-type-html",
  py: "file-type-python",
  sh: "file-type-shell",
  bash: "file-type-shell",
  yml: "file-type-yaml",
  yaml: "file-type-yaml",
  toml: "file-type-toml",
  xml: "file-type-xml",
  svg: "file-type-svg",
  png: "file-type-image",
  jpg: "file-type-image",
  jpeg: "file-type-image",
  gif: "file-type-image",
  webp: "file-type-image",
  ico: "file-type-image",
  txt: "file-type-text",
  env: "file-type-dotenv",
  gitignore: "file-type-git",
  dockerignore: "file-type-docker2",
  dockerfile: "file-type-docker2",
  lock: "file-type-lock",
  sql: "file-type-sql",
  graphql: "file-type-graphql",
  gql: "file-type-graphql",
  rs: "file-type-rust",
  go: "file-type-go",
  java: "file-type-java",
  rb: "file-type-ruby",
  php: "file-type-php",
  c: "file-type-c",
  cpp: "file-type-cpp",
  h: "file-type-c",
  hpp: "file-type-cpp",
  swift: "file-type-swift",
  kt: "file-type-kotlin",
  vue: "file-type-vue",
  svelte: "file-type-svelte",
  astro: "file-type-astro",
};

const FILENAME_TO_ICON: Record<string, string> = {
  "package.json": "file-type-node",
  "package-lock.json": "file-type-npm",
  "tsconfig.json": "file-type-typescript",
  "jsconfig.json": "file-type-jsconfig",
  ".gitignore": "file-type-git",
  ".env": "file-type-dotenv",
  ".env.local": "file-type-dotenv",
  ".env.example": "file-type-dotenv",
  dockerfile: "file-type-docker2",
  "docker-compose.yml": "file-type-docker2",
  "readme.md": "file-type-markdown",
  license: "file-type-license",
  "license.md": "file-type-license",
  ".eslintrc": "file-type-eslint",
  ".eslintrc.json": "file-type-eslint",
  ".prettierrc": "file-type-prettier",
  "vite.config.ts": "file-type-vite",
  "vite.config.js": "file-type-vite",
  "tailwind.config.js": "file-type-tailwind",
  "tailwind.config.ts": "file-type-tailwind",
  "bun.lock": "file-type-bun",
  "bun.lockb": "file-type-bun",
  "bunfig.toml": "file-type-bun",
};

const FOLDER_TO_ICON: Record<string, string> = {
  src: "folder-type-src",
  test: "folder-type-test",
  tests: "folder-type-test",
  __tests__: "folder-type-test",
  lib: "folder-type-lib",
  dist: "folder-type-dist",
  build: "folder-type-dist",
  node_modules: "folder-type-node",
  config: "folder-type-config",
  public: "folder-type-public",
  assets: "folder-type-asset",
  images: "folder-type-images",
  components: "folder-type-component",
  pages: "folder-type-view",
  views: "folder-type-view",
  routes: "folder-type-route",
  api: "folder-type-api",
  utils: "folder-type-helper",
  helpers: "folder-type-helper",
  hooks: "folder-type-hook",
  styles: "folder-type-css",
  docs: "folder-type-docs",
};

function resolveIconName(fileName: string, type: "file" | "directory", isOpen?: boolean): string {
  const lowerName = fileName.toLowerCase();

  if (type === "directory") {
    const folderIcon = FOLDER_TO_ICON[lowerName];
    if (folderIcon) {
      const openedKey = `${folderIcon}-opened`;
      if (isOpen && icons[openedKey]) return openedKey;
      return icons[folderIcon] ? folderIcon : "default-folder";
    }
    return isOpen ? "default-folder-opened" : "default-folder";
  }

  if (lowerName.includes(".test.") || lowerName.includes(".spec.")) {
    const ext = lowerName.split(".").pop();
    const testKey = `file-type-test${ext}`;
    if (icons[testKey]) return testKey;
  }

  const filenameIcon = FILENAME_TO_ICON[lowerName];
  if (filenameIcon && icons[filenameIcon]) return filenameIcon;

  const ext = lowerName.split(".").pop() || "";
  const extIcon = EXT_TO_ICON[ext];
  if (extIcon && icons[extIcon]) return extIcon;

  return "default-file";
}

export function resolveFileIconSvg(
  name: string,
  type: "file" | "directory",
  isOpen?: boolean,
): { body: string; viewBox: string } {
  const iconName = resolveIconName(name, type, isOpen);
  const body = icons[iconName]?.body ?? icons["default-file"]?.body ?? "";
  return { body, viewBox: `0 0 ${defaultSize} ${defaultSize}` };
}
