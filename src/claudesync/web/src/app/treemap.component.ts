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

    const plotlyData = [{
      type: 'treemap',
      labels: data.labels,
      parents: data.parents,
      values: data.values,
      ids: data.ids,
      textinfo: 'label+value',
      hovertemplate: `
        <b>%{label}</b><br>
        Size: %{value} bytes<br>
        <extra></extra>
      `,
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
    chartContainer.on('plotly_click', (data: any) => {
      if (data.points && data.points.length > 0) {
        const point = data.points[0];
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
