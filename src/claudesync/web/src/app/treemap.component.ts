import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FileDataService } from './file-data.service';
import { HttpClient } from '@angular/common/http';
import {finalize, Subject} from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import {FileInfo, SelectedNode, TreemapData, TreeNode} from './treemap.types';

declare const Plotly: any;

@Component({
  selector: 'app-treemap',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './treemap.component.html',
  styleUrls: ['./treemap.component.css']
})
export class TreemapComponent implements OnInit, OnDestroy {
  selectedNode: SelectedNode | null = null;
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
    this.http.get<TreemapData>(`${this.baseUrl}/treemap`)
      .pipe(
        takeUntil(this.destroy$),
        finalize(() => this.isLoading = false)
      )
      .subscribe({
        next: (data) => {
          this.renderTreemap(data);
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

    this.files = data.ids.map((id, index) => ({
      path: id,
      size: data.values[index],
      included: data.included[index]
    })).filter(file => {
      // Only include leaf nodes (actual files)
      return file.included;
    }).sort((a, b) => a.path.localeCompare(b.path));

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
