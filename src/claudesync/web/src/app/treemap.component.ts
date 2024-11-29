import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FileDataService } from './file-data.service';

interface TreeNode {
  name: string;
  size: number;
  type: string;
  children?: TreeNode[];
}

interface SelectedNode {
  path: string;
  type: string;
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
export class TreemapComponent implements OnInit {
  availableTypes: string[] = ['Source', 'Config', 'Asset', 'Documentation'];
  activeTypes: Set<string> = new Set(this.availableTypes);
  selectedNode: SelectedNode | null = null;
  private treeData: TreeNode | null = null;

  constructor(private fileDataService: FileDataService) {}

  ngOnInit() {
    this.loadData();
  }

  private loadData() {
    // TODO: Implement actual data loading from FileDataService
    // For now using mock data
    const exampleData = {
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

    this.renderTreemap();
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

  private renderTreemap() {
    // TODO: Implement actual treemap visualization
    console.log('Rendering treemap with filtered data');
  }

  formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  }
}
