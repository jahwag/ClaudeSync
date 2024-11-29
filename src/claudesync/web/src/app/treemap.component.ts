import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FileDataService } from './file-data.service';
import { HttpClient } from '@angular/common/http';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

declare const Plotly: any;

interface TreemapData {
  labels: string[];
  parents: string[];
  values: number[];
  ids: string[];
}

interface SelectedNode {
  path: string;
  size: number;
  totalSize: number;
}

interface TreeNode {
  id: string;
  label: string;
  value: number;
  children: TreeNode[];
}

@Component({
  selector: 'app-treemap',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './treemap.component.html',
  styleUrls: ['./treemap.component.css']
})
export class TreemapComponent implements OnInit, OnDestroy {
  selectedNode: SelectedNode | null = null;
  private destroy$ = new Subject<void>();
  private baseUrl = 'http://localhost:4201/api';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadTreemapData();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
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

  private countFiles(node: TreeNode): number {
    // If node has no children, it's a file
    if (node.children.length === 0) {
      return 1;
    }
    // If node has children, sum up all files in children
    return node.children.reduce((sum, child) => sum + this.countFiles(child), 0);
  }

  private loadTreemapData() {
    this.http.get<TreemapData>(`${this.baseUrl}/treemap`)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.renderTreemap(data);
        },
        error: (error) => {
          console.error('Error loading treemap data:', error);
        }
      });
  }

  private renderTreemap(data: TreemapData) {
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

    const plotlyData = [{
      type: 'treemap',
      branchvalues: "total",
      labels: data.labels,
      parents: data.parents,
      values: data.values,
      ids: data.ids,
      textinfo: 'label+value',
      hovertemplate: (d: any) => {
        const nodeId = d.id;
        const fileCount = fileCountMap.get(nodeId) || 0;
        const sizeText = this.formatSize(d.value);
        return `
          <b>${d.label}</b><br>
          Size: ${sizeText}<br>
          Files: ${fileCount}<br>
          <extra></extra>
        `;
      },
      marker: {
        colorscale: 'Blues',
        showscale: true
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
      treemapcolorway: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
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
