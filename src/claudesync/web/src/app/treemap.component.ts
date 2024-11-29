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
    this.treeData = {
      name: 'root',
      size: 0,
      type: 'root',
      children: [
        {
          name: 'src',
          size: 1024000,
          type: 'Source',
          children: [
            {
              name: 'app',
              size: 512000,
              type: 'Source'
            }
          ]
        },
        {
          name: 'docs',
          size: 256000,
          type: 'Documentation'
        }
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
