import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FileDataService } from './file-data.service';

declare const Plotly: any;

interface TreeNode {
  name: string;
  size?: number;
  children?: TreeNode[];
}

interface SelectedNode {
  path: string;
  size: number;
  totalSize: number;
}

interface PlotData {
  labels: string[];
  parents: string[];
  values: number[];
  ids: string[];
}

@Component({
  selector: 'app-treemap',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './treemap.component.html',
  styleUrls: ['./treemap.component.css']
})
export class TreemapComponent implements OnInit {
  selectedNode: SelectedNode | null = null;
  private treeData: TreeNode | null = null;

  // Example data structure remains the same
  private exampleData: TreeNode = {
    name: 'root',
    children: [
      {
        name: 'src',
        children: [
          {
            name: 'components',
            children: [
              { name: 'Header.tsx', size: 2450 },
              { name: 'Footer.tsx', size: 1280 },
              { name: 'Sidebar.tsx', size: 3400 }
            ]
          },
          {
            name: 'utils',
            children: [
              { name: 'formatters.ts', size: 890 },
              { name: 'helpers.ts', size: 1200 }
            ]
          },
          { name: 'index.ts', size: 340 }
        ]
      },
      {
        name: 'public',
        children: [
          { name: 'favicon.ico', size: 4500 },
          { name: 'logo.svg', size: 2800 }
        ]
      },
      {
        name: 'docs',
        children: [
          { name: 'README.md', size: 1500 },
          { name: 'CONTRIBUTING.md', size: 2100 },
          { name: 'API.md', size: 3400 }
        ]
      },
      { name: 'package.json', size: 720 },
      { name: 'tsconfig.json', size: 480 }
    ]
  };

  constructor(private fileDataService: FileDataService) {}

  ngOnInit() {
    this.loadData();
  }

  private loadData() {
    this.treeData = this.exampleData;
    this.renderTreemap();
  }

  private calculateFolderSize(node: TreeNode): number {
    if (node.size !== undefined) {
      return node.size;
    }

    let totalSize = 0;
    if (node.children) {
      node.children.forEach(child => {
        totalSize += this.calculateFolderSize(child);
      });
    }
    return totalSize;
  }

  private flattenHierarchy(node: TreeNode, parent: string, plotData: PlotData) {
    const nodeId = parent ? `${parent}/${node.name}` : node.name;

    plotData.ids.push(nodeId);
    plotData.labels.push(node.name);
    plotData.parents.push(parent);

    if (node.size !== undefined) {
      plotData.values.push(node.size);
    } else {
      const totalSize = this.calculateFolderSize(node);
      plotData.values.push(totalSize);
    }

    if (node.children) {
      node.children.forEach(child => {
        this.flattenHierarchy(child, nodeId, plotData);
      });
    }
  }

  private renderTreemap() {
    const chartContainer = document.getElementById('file-treemap');
    if (!chartContainer || !this.treeData) {
      console.warn('Chart container or tree data not available');
      return;
    }

    const plotData: PlotData = {
      labels: [],
      parents: [],
      values: [],
      ids: []
    };

    this.flattenHierarchy(this.treeData, '', plotData);

    const data = [{
      type: 'treemap',
      ids: plotData.ids,
      labels: plotData.labels,
      parents: plotData.parents,
      values: plotData.values,
      textinfo: 'label+value',
      hovertemplate: `
        <b>%{label}</b><br>
        Size: %{value} bytes<br>
        <extra></extra>
      `,
      marker: {
        colorscale: 'Blues'
      },
      textposition: 'middle center',
      branchvalues: 'total',
      pathbar: {
        visible: true,  // Enable the navigation path bar
        side: 'top',   // Position it at the top
        thickness: 20   // Make it thick enough to be clickable
      }
    }];

    const layout = {
      width: chartContainer.offsetWidth,
      height: 400,
      margin: { l: 0, r: 0, t: 30, b: 0 }
    };

    const config = {
      displayModeBar: false,  // Hide the modebar
      responsive: true
    };

    Plotly.newPlot('file-treemap', data, layout), config;

    // Handle click events
    // @ts-ignore
    chartContainer.on('plotly_click', (data: any) => {
      if (data.points && data.points.length > 0) {
        const point = data.points[0];
        this.selectedNode = {
          path: plotData.ids[point.pointIndex],
          size: plotData.values[point.pointIndex],
          totalSize: plotData.values[point.pointIndex]
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
