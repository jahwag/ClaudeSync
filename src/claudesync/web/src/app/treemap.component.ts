import {Component, OnInit, OnDestroy, Input, EventEmitter, Output} from '@angular/core';
import { CommonModule } from '@angular/common';
import {FileContentResponse, FileDataService, SyncData} from './file-data.service';
import { HttpClient } from '@angular/common/http';
import {finalize} from 'rxjs/operators';
import { takeUntil } from 'rxjs/operators';
import {FileInfo, SelectedNode, TreemapData, TreeNode} from './treemap.types';
import {FormsModule} from '@angular/forms';
import {FilePreviewComponent} from './file-preview.component';
import {ModalComponent} from './modal.component';
import {Subject, Subscription} from 'rxjs';
import { NodeActionsMenuComponent } from './node-actions-menu.component';
import { DropZoneComponent, DroppedFile } from './drop-zone.component';
import { NotificationService } from './notification.service';

declare const Plotly: any;

@Component({
  selector: 'app-treemap',
  standalone: true,
  imports: [CommonModule, FormsModule, FilePreviewComponent, ModalComponent, DropZoneComponent],
  templateUrl: './treemap.component.html',
  styleUrls: ['./treemap.component.css']
})
export class TreemapComponent implements OnDestroy {
  @Input() set syncData(data: SyncData | null) {
    if (data) {
      console.debug('TreemapComponent received new syncData');
      this.originalTreeData = data.treemap;
      this.updateTreemap();
    }
  }

  @Output() reloadRequired = new EventEmitter<void>();

  selectedNode: SelectedNode | null = null;
  showOnlyIncluded = true;
  showFileList = false
  private destroy$ = new Subject<void>();
  private baseUrl = 'http://localhost:4201/api';

  selectedFile: FileInfo | null = null;
  fileContent: string | null = null;
  fileContentError: string | null = null;

  private originalTreeData: any = null;

  files: FileInfo[] = [];
  private fileNodeMap = new Map<string, FileInfo>();

  filterText = '';

  private currentSubscription?: Subscription;

  constructor(
    private http: HttpClient,
    private fileDataService: FileDataService,
    private notificationService: NotificationService
  ) {}

  ngOnDestroy() {
    this.currentSubscription?.unsubscribe();

    this.destroy$.next();
    this.destroy$.complete();
    // Clean up Plotly events
    const chartContainer = document.getElementById('file-treemap');
    if (chartContainer) {
      Plotly.purge(chartContainer);
    }
  }

  private filterTree(node: any): any {
    if (!this.showOnlyIncluded) {
      return node;
    }

    if (!node.children) {
      // Leaf node (file)
      return node.included ? node : null;
    }

    // Filter children recursively
    const filteredChildren = (node.children || [])
      // @ts-ignore
      .map(child => this.filterTree(child))
      // @ts-ignore
      .filter(child => child !== null);

    if (filteredChildren.length === 0) {
      return null;
    }

    return {
      ...node,
      children: filteredChildren
    };
  }

  public updateTreemap() {
    if (!this.originalTreeData) return;

    const filteredData = this.filterTree(this.originalTreeData);
    if (filteredData) {
      const plotlyData = this.flattenTree(filteredData);
      this.renderTreemap(plotlyData);
      this.updateFilesList(this.originalTreeData);
    }
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
    this.fileNodeMap.clear();

    const processNode = (node: any, parentPath: string = '') => {
      const currentPath = parentPath ? `${parentPath}/${node.name}` : node.name;

      if ('size' in node) {
        // This is a file node
        const pathParts = currentPath.split('/');
        pathParts.shift(); // Remove the first element (root directory name)
        const fileName = pathParts.pop() || '';
        const filePath = pathParts.join('/');

        const fileInfo: FileInfo = {
          name: fileName,
          path: filePath,
          fullPath: currentPath,
          size: node.size,
          included: node.included
        };

        files.push(fileInfo);
        this.fileNodeMap.set(currentPath, fileInfo);
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
    let filtered = this.files;

    if (this.showOnlyIncluded) {
      filtered = filtered.filter(f => f.included);
    }

    if (this.filterText.trim()) {
      const searchText = this.filterText.toLowerCase();
      filtered = filtered.filter(f =>
        f.name.toLowerCase().includes(searchText) ||
        f.path.toLowerCase().includes(searchText) ||
        `${f.path}/${f.name}`.toLowerCase().includes(searchText)
      );
    }

    return filtered;
  }

  private getNodeInclusionStatus(node: any): 'included' | 'excluded' | 'partial' {
    if (!node.children) {
      // For leaf nodes (files), directly use the included property
      return node.included ? 'included' : 'excluded';
    }

    // For directories, check children recursively
    let hasIncluded = false;
    let hasExcluded = false;

    const checkChildren = (childNode: any) => {
      if (!childNode.children) {
        // Leaf node
        if (childNode.included) {
          hasIncluded = true;
        } else {
          hasExcluded = true;
        }
      } else {
        // Directory node - process all children
        childNode.children.forEach(checkChildren);
      }
    };

    // Process all children
    node.children.forEach(checkChildren);

    // Determine status based on children
    if (hasIncluded && hasExcluded) {
      return 'partial';
    } else if (hasIncluded) {
      return 'included';
    } else {
      return 'excluded';
    }
  }

  private findNodeInTree(tree: any, nodeName: string): any {
    if (tree.name === nodeName) {
      return tree;
    }

    if (tree.children) {
      for (const child of tree.children) {
        const found = this.findNodeInTree(child, nodeName);
        if (found) return found;
      }
    }

    return null;
  }

  clearFilter() {
    this.filterText = '';
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
    const inclusionStatusMap = new Map<string, string>();  // Added this line

    // Calculate file counts for each node
    for (const [id, node] of nodeMap) {
      fileCountMap.set(id, this.countFiles(node));
    }

    // Process nodes to calculate file counts and inclusion status
    const processNode = (id: string) => {
      const node = nodeMap.get(id);
      if (!node) return;

      // Calculate file count
      fileCountMap.set(id, this.countFiles(node));

      // Calculate inclusion status by checking the original tree data
      let treeNode = this.findNodeInTree(this.originalTreeData, node.label);
      if (treeNode) {
        inclusionStatusMap.set(id, this.getNodeInclusionStatus(treeNode));
      }

      // Process children
      node.children.forEach(child => processNode(child.id));
    };

    // Start processing from root nodes (nodes with no parents)
    data.ids.forEach((id, index) => {
      if (!data.parents[index]) {
        processNode(id);
      }
    });
    // Create custom text array for hover info
    const customData = data.ids.map((id, index) => ({
      fileCount: fileCountMap.get(id) || 0,
      sizeFormatted: this.formatSizeForHover(nodeMap.get(id)?.value || 0),
      included: inclusionStatusMap.get(id),
      isFile: !nodeMap.get(id)?.children?.length
    }));

    // Create color array based on included status
    const colors = data.ids.map(id => {
      const status = inclusionStatusMap.get(id);
      switch (status) {
        case 'included':
          return '#4f46e5'; // Indigo for included
        case 'partial':
          return '#eab308'; // Yellow for partially included
        default:
          return '#94a3b8'; // Gray for excluded
      }
    });

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
      height: 800,
      margin: { l: 0, r: 0, t: 30, b: 0 },
    };

    const config = {
      displayModeBar: false,
      responsive: true
    };

    // Create the plot and attach the click handler
    Plotly.newPlot('file-treemap', plotlyData, layout, config);

    // Handle click events
    // @ts-ignore
    chartContainer.on('plotly_click', (d: any) => {
      if (d.points && d.points.length > 0) {
        const point = d.points[0];
        const customData = point.customdata;

        this.selectedNode = {
          path: point.id,
          size: point.value,
          totalSize: point.value
        };

        console.log('Selected node:', this.selectedNode);

        // If clicked node is a file, show preview
        if (customData.isFile) {
          const fileInfo = this.fileNodeMap.get(point.id);
          if (fileInfo) {
            this.viewFileContent(fileInfo);
          }
        }
      }
    });
  }

  clearSelection() {
    this.selectedNode = null;
  }

  copySelection() {
    if (this.selectedNode) {
      // Remove the "root/" prefix if it exists
      const path = this.selectedNode.path.replace(/^root\//, '');
      navigator.clipboard.writeText(path).then(() => {
        // Optional: You could add a temporary visual feedback here
        console.log('Path copied to clipboard:', path);
      }).catch(err => {
        console.error('Failed to copy text: ', err);
      });
    }
  }

  getSelection(): string {
    if (this.selectedNode) {
      // Remove the "root/" prefix if it exists
      return this.selectedNode.path.replace(/^root\//, '');
    }
    return '';
  }

  formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  }

  viewFileContent(file: FileInfo) {
    this.selectedFile = file;
    this.fileContent = null;
    this.fileContentError = null;

    const fullPath = file.path ? `${file.path}/${file.name}` : file.name;

    this.fileDataService.getFileContent(fullPath)
      .subscribe({
        next: (response: FileContentResponse) => {
          if (response.error) {
            this.fileContentError = response.error;
          } else {
            this.fileContent = response.content;
          }
        },
        error: (error) => {
          console.error('Error loading file content:', error);
          this.fileContentError = 'Failed to load file content';
        }
      });
  }

  closeFileContent() {
    this.selectedFile = null;
    this.fileContent = null;
    this.fileContentError = null;
  }

  onShowOnlyIncludedChange() {
    this.updateTreemap();
  }

  handleNodeAction(action: string) {
    if (!this.selectedNode) return;

    // Remove the "root/" prefix if it exists
    const path = this.selectedNode.path.replace(/^root\//, '');

    switch (action) {
      case 'copy':
        this.copySelection();
        break;

      case 'addToIncludes':
        this.updateConfigIncrementally({
          action: 'addInclude',
          pattern: path
        });
        break;

      case 'removeFromIncludes':
        this.updateConfigIncrementally({
          action: 'removeInclude',
          pattern: path
        });
        break;

      case 'addToExcludes':
        this.updateConfigIncrementally({
          action: 'addExclude',
          pattern: path
        });
        break;

      case 'removeFromExcludes':
        this.updateConfigIncrementally({
          action: 'removeExclude',
          pattern: path
        });
        break;

      case 'clear':
        this.clearSelection();
        break;
    }
  }

  private updateConfigIncrementally(config: { action: string, pattern: string }) {
    this.fileDataService.updateConfigIncrementally(config)
      .subscribe({
        next: (response) => {
          // Instead of refreshing cache here, emit up to parent
          this.reloadRequired.emit();
        },
        error: (error) => {
          console.error('Error updating configuration:', error);
        }
      });
  }

  onFilesDropped(files: DroppedFile[]): void {
    if (!files.length) return;

    this.notificationService.info(`Processing ${files.length} file(s)...`);

    this.fileDataService.resolveDroppedFiles(files)
      .subscribe({
        next: (response) => {
          if (!response.success) {
            this.notificationService.error('Failed to process files');
            return;
          }

          const results = response.results || [];
          const resolvedFiles = results.filter((r: any) => r.resolved);
          const unresolvedFiles = results.filter((r: any) => !r.resolved);

          // Process successful matches
          if (resolvedFiles.length > 0) {
            // Add resolved paths to includes
            this.processResolvedFiles(resolvedFiles);
            this.notificationService.success(
              `Successfully matched and added ${resolvedFiles.length} file(s)`
            );
          }

          // Notify about unresolved files
          if (unresolvedFiles.length > 0) {
            this.notificationService.warning(
              `Could not match ${unresolvedFiles.length} file(s) to project content`
            );
          }
        },
        error: (error) => {
          console.error('Error processing dropped files:', error);
          this.notificationService.error('Failed to process dropped files');
        }
      });
  }

  private processResolvedFiles(resolvedFiles: any[]): void {
    // Extract all unique paths from resolved files
    const pathsToAdd: string[] = [];

    resolvedFiles.forEach(file => {
      // For each file that was resolved, extract the paths
      (file.paths || []).forEach((path: string) => {
        if (!pathsToAdd.includes(path)) {
          pathsToAdd.push(path);
        }
      });
    });

    // Add each path to the includes list
    pathsToAdd.forEach((path, index) => {
      setTimeout(() => {
        this.updateConfigIncrementally({
          action: 'addInclude',
          pattern: path
        });
      }, index * 200); // Stagger updates to avoid race conditions
    });

    // After all paths are added, trigger a reload
    setTimeout(() => {
      this.reloadRequired.emit();
    }, pathsToAdd.length * 200 + 300);
  }
}
