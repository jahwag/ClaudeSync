export interface TreemapData {
  labels: string[];
  parents: string[];
  values: number[];
  ids: string[];
  included: boolean[];
}

export interface SelectedNode {
  path: string;
  size: number;
  totalSize: number;
}

export interface TreeNode {
  id: string;
  label: string;
  value: number;
  children: TreeNode[];
}

export interface FileInfo {
  path: string;
  size: number;
  included: boolean;
}
