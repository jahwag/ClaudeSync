export interface TreeNode {
  id: string;
  label: string;
  value: number;
  children: TreeNode[];
}

export interface TreemapData {
  labels: string[];
  parents: string[];
  values: number[];
  ids: string[];
  included: boolean[];
}

export interface FileInfo {
  name: string;  // Just the file name
  path: string;  // Full path excluding file name
  fullPath: string; // Complete path including file name
  size: number;
  included: boolean;
}

export interface SelectedNode {
  path: string;
  size: number;
  totalSize: number;
}
