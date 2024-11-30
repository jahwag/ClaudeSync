import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FileDataService } from './file-data.service';
import { HttpClient } from '@angular/common/http';
import {finalize, Subject} from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import {FileInfo, SelectedNode, TreemapData, TreeNode} from './treemap.types';
import {FormsModule} from '@angular/forms';

declare const Plotly: any;

@Component({
  selector: 'app-treemap',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './treemap.component.html',
  styleUrls: ['./treemap.component.css']
})
export class TreemapComponent implements OnInit, OnDestroy {
  selectedNode: SelectedNode | null = null;
  showOnlyIncluded = false;
  isLoading = false;
  showFileList = false
  private destroy$ = new Subject<void>();
  private baseUrl = 'http://localhost:4201/api';

  files: FileInfo[] = [];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadTreemapData();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private flattenTree(node: any, parentId: string = ''): TreemapData {
    const data: TreemapData = {
      labels: [],
      parents: [],
      values: [],
      ids: [],
      included: []
    };

    // Calculate directory sizes first
    const calculateSize = (node: any): number => {
      if ('size' in node) {
        return node.size;
      }
      return (node.children || []).reduce((sum: number, child: any) => sum + calculateSize(child), 0);
    };

    const processNode = (node: any, parentId: string) => {
      const currentId = parentId ? `${parentId}/${node.name}` : node.name;

      data.labels.push(node.name);
      data.parents.push(parentId);
      data.ids.push(currentId);

      // For both files and directories, calculate the total size
      const totalSize = calculateSize(node);
      data.values.push(totalSize);

      // For files, use the included property directly
      // For directories, check if any children are included
      const isIncluded = 'included' in node ? node.included :
        (node.children || []).some((child: any) =>
          'included' in child ? child.included : false
        );
      data.included.push(isIncluded);

      // Process children if they exist
      if (node.children) {
        node.children.forEach((child: any) => {
          processNode(child, currentId);
        });
      }
    };

    processNode(node, '');
    return data;
  }

  private updateFilesList(treeData: any) {
    const files: FileInfo[] = [];

    const processNode = (node: any, parentPath: string = '') => {
      const currentPath = parentPath ? `${parentPath}/${node.name}` : node.name;

      if ('size' in node) {
        // This is a file node
        const pathParts = currentPath.split('/');
        const fileName = pathParts.pop() || '';
        const filePath = pathParts.join('/');

        files.push({
          name: fileName,
          path: filePath,
          fullPath: currentPath,
          size: node.size,
          included: node.included
        });
      } else if (node.children) {
        // This is a directory node - process its children
        node.children.forEach((child: any) => processNode(child, currentPath));
      }
    };

    processNode(treeData);
    this.files = files.sort((a, b) => a.fullPath.localeCompare(b.fullPath));
  }

  private buildTree(data: TreemapData): Map<string, TreeNode> {
    const nodeMap = new Map<string, TreeNode>();

    // First pass: create all nodes
    for (let i = 0; i < data.ids.length; i++) {
      nodeMap.set(data.ids[i], {
        id: data.ids[i],
        label: data.labels[i],
        value: data.values[i],
        children: []
      });
    }

    // Second pass: build relationships
    for (let i = 0; i < data.ids.length; i++) {
      const parentId = data.parents[i];
      if (parentId && nodeMap.has(parentId)) {
        const parent = nodeMap.get(parentId)!;
        parent.children.push(nodeMap.get(data.ids[i])!);
      }
    }

    return nodeMap;
  }

  getIncludedFilesCount(): number {
    return this.files.filter(f => f.included).length;
  }

  get filteredFiles(): FileInfo[] {
    if (this.showOnlyIncluded) {
      return this.files.filter(f => f.included);
    }
    return this.files;
  }

  private countFiles(node: TreeNode): number {
    if (node.children.length === 0) {
      return 1;
    }
    return node.children.reduce((sum, child) => sum + this.countFiles(child), 0);
  }

  private formatSizeForHover(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }

  private loadTreemapData() {
    this.isLoading = true;
    this.http.get<any>(`${this.baseUrl}/treemap`)
      .pipe(
        takeUntil(this.destroy$),
        finalize(() => this.isLoading = false)
      )
      .subscribe({
        next: (treeData) => {
          const plotlyData = this.flattenTree(treeData);
          this.renderTreemap(plotlyData);
          this.updateFilesList(treeData);
        },
        error: (error) => {
          console.error('Error loading treemap data:', error);
        }
      });
  }

  public reload() {
    this.loadTreemapData();
  }

  private renderTreemap(data: TreemapData) {
    this.updateFilesList(data);
    const chartContainer = document.getElementById('file-treemap');
    if (!chartContainer) {
      console.warn('Chart container not found');
      return;
    }

    // Build tree structure and calculate file counts
    const nodeMap = this.buildTree(data);
    const fileCountMap = new Map<string, number>();

    // Calculate file counts for each node
    for (const [id, node] of nodeMap) {
      fileCountMap.set(id, this.countFiles(node));
    }

    // Create custom text array for hover info
    const customData = data.ids.map((id, index) => ({
      fileCount: fileCountMap.get(id) || 0,
      sizeFormatted: this.formatSizeForHover(nodeMap.get(id)?.value || 0),
      included: data.included[index] ? "Included" : "Not Included"
    }));

    // Create color array based on included status
    const colors = data.included.map(included => included ? '#4f46e5' : '#94a3b8');

    const plotlyData = [{
      type: 'treemap',
      branchvalues: "total",
      labels: data.labels,
      parents: data.parents,
      values: data.values,
      ids: data.ids,
      textinfo: 'label',
      customdata: customData,
      hovertemplate: `
<b>%{label}</b><br>
Size: %{customdata.sizeFormatted}<br>
Files: %{customdata.fileCount}<br>
Status: %{customdata.included}<br>
<extra></extra>`,
      marker: {
        colors: colors,
        showscale: false
      },
      pathbar: {
        visible: true,
        side: 'top',
        thickness: 20
      }
    }];

    const layout = {
      width: chartContainer.offsetWidth,
      height: 400,
      margin: { l: 0, r: 0, t: 30, b: 0 },
    };

    const config = {
      displayModeBar: false,
      responsive: true
    };

    Plotly.newPlot('file-treemap', plotlyData, layout, config);

    // Handle click events
    // @ts-ignore
    chartContainer.on('plotly_click', (d: any) => {
      if (d.points && d.points.length > 0) {
        const point = d.points[0];
        this.selectedNode = {
          path: point.id,
          size: point.value,
          totalSize: point.value
        };
      }
    });
  }

  clearSelection() {
    this.selectedNode = null;
  }

  formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  }
}
