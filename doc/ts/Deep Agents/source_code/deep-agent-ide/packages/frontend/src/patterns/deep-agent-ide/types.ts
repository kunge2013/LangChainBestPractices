export interface FileEntry {
  name: string;
  type: "file" | "directory";
  path: string;
  size: number;
}

export interface FileTreeNode extends FileEntry {
  children?: FileTreeNode[];
  isOpen?: boolean;
}

export interface FileSnapshot {
  [path: string]: string;
}
