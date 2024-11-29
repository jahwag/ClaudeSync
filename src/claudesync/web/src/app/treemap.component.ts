import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FileDataService } from './file-data.service';

declare const Plotly: any;

interface TreeNode {
  name: string;
  size?: number;
  type?: string;
  children?: TreeNode[];
}

interface SelectedNode {
  path: string;
  type: string;
  size: number;
  totalSize: number;
}

interface PlotData {
  labels: string[];
  parents: string[];
  values: number[];
  ids: string[];
  types: string[];
}

@Component({
  selector: 'app-treemap',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './treemap.component.html',
  styleUrls: ['./treemap.component.css']
})
export class TreemapComponent implements OnInit {
  availableTypes: string[] = ['Source', 'Config', 'Asset', 'Documentation'];
  activeTypes: Set<string> = new Set(this.availableTypes);
  selectedNode: SelectedNode | null = null;
  private treeData: TreeNode | null = null;

  // Example data as provided
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

  private flattenHierarchy(node: TreeNode, parent: string, plotData: PlotData) {
    const nodeId = parent ? `${parent}/${node.name}` : node.name;

    // Add this node to the plot data
    plotData.ids.push(nodeId);
    plotData.labels.push(node.name);
    plotData.parents.push(parent);

    // For files (nodes with size), use the size directly
    // For folders (nodes without size), sum up children's sizes
    if (node.size !== undefined) {
      plotData.values.push(node.size);
      // Determine file type based on extension
      plotData.types.push(this.getFileType(node.name));
    } else {
      let totalSize = 0;
      if (node.children) {
        node.children.forEach(child => {
          if (child.size) {
            totalSize += child.size;
          }
        });
      }
      plotData.values.push(totalSize);
      plotData.types.push('folder');
    }

    // Recursively process children
    if (node.children) {
      node.children.forEach(child => {
        this.flattenHierarchy(child, nodeId, plotData);
      });
    }
  }

  private getFileType(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (!ext) return 'unknown';

    const typeMap: { [key: string]: string } = {
      'ts': 'Source',
      'tsx': 'Source',
      'js': 'Source',
      'jsx': 'Source',
      'json': 'Config',
      'ico': 'Asset',
      'svg': 'Asset',
      'png': 'Asset',
      'jpg': 'Asset',
      'md': 'Documentation'
    };

    return typeMap[ext] || 'unknown';
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
      ids: [],
      types: []
    };

    this.flattenHierarchy(this.treeData, '', plotData);

    // Filter data based on active types
    const filteredIndices = plotData.types.map((type, index) =>
      this.activeTypes.has(type) || type === 'folder' ? index : -1
    ).filter(i => i !== -1);

    const data = [{
      type: 'treemap',
      ids: filteredIndices.map(i => plotData.ids[i]),
      labels: filteredIndices.map(i => plotData.labels[i]),
      parents: filteredIndices.map(i => plotData.parents[i]),
      values: filteredIndices.map(i => plotData.values[i]),
      textinfo: 'label+value',
      hovertemplate: `
        <b>%{label}</b><br>
        Size: %{value} bytes<br>
        <extra></extra>
      `,
      marker: {
        colors: filteredIndices.map(i => {
          const type = plotData.types[i];
          switch(type) {
            case 'Source': return '#4CAF50';
            case 'Config': return '#2196F3';
            case 'Asset': return '#FFC107';
            case 'Documentation': return '#9C27B0';
            default: return '#E0E0E0';
          }
        })
      }
    }];

    const layout = {
      width: chartContainer.offsetWidth,
      height: 400,
      margin: { l: 0, r: 0, t: 0, b: 0 }
    };

    Plotly.newPlot('file-treemap', data, layout);

    // Handle click events
    // @ts-ignore
    chartContainer.on('plotly_click', (data: any) => {
      if (data.points && data.points.length > 0) {
        const point = data.points[0];
        const index = filteredIndices[point.pointIndex];

        this.selectedNode = {
          path: plotData.ids[index],
          type: plotData.types[index],
          size: plotData.values[index],
          totalSize: plotData.values[index]
        };
      }
    });
  }

  toggleType(type: string) {
    if (this.activeTypes.has(type)) {
      this.activeTypes.delete(type);
    } else {
      this.activeTypes.add(type);
    }
    this.renderTreemap();
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
