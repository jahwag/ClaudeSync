import {Component, OnInit, ViewChild} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import {FileDataService, SyncStats, FileConfig, SyncData} from './file-data.service';
import {TreemapComponent} from './treemap.component';
import {finalize} from 'rxjs/operators';
import {Project, ProjectDropdownComponent} from './project-dropdown.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule, TreemapComponent, ProjectDropdownComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  providers: [FileDataService]
})
export class AppComponent implements OnInit {
  configVisible = false;
  fileCategories = '';
  claudeignore = '';
  isLoading = false;
  stats: SyncStats = {
    filesToSync: 0,
    totalSize: '0 B'
  };

  syncData: SyncData | null = null;

  projects: Project[] = [];
  selectedProject: string = '';

  @ViewChild(TreemapComponent) treemapComponent!: TreemapComponent;

  constructor(private fileDataService: FileDataService) {}

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.isLoading = true;
    this.fileDataService.getProjects()
      .pipe(finalize(() => this.isLoading = false))
      .subscribe({
        next: (projects) => {
          this.projects = projects;
          // Select the first project by default if none is selected
          if (projects.length > 0 && !this.selectedProject) {
            this.selectedProject = projects[0].path;
            this.loadData();
          }
        },
        error: (error) => {
          console.error('Error loading projects:', error);
        }
      });
  }

  onProjectChange(projectPath: string) {
    this.selectedProject = projectPath;
    this.isLoading = true;

    // Clear the current data before loading new project
    this.fileDataService.clearCache();

    this.fileDataService.setActiveProject(projectPath)
      .subscribe({
        next: () => {
          // After setting the project, trigger a full reload
          this.reload();
        },
        error: (error) => {
          console.error('Error setting active project:', error);
          this.isLoading = false;
        }
      });
  }

  loadData() {
    this.isLoading = true;
    this.fileDataService.getSyncData()
      .pipe(finalize(() => this.isLoading = false))
      .subscribe({
        next: (data) => {
          this.syncData = data;
          this.fileCategories = JSON.stringify(data.config.fileCategories, null, 2);
          this.claudeignore = data.config.claudeignore;
          this.stats = data.stats;
        },
        error: (error) => {
          console.error('Error loading data:', error);
        }
      });
  }

  toggleConfig() {
    this.configVisible = !this.configVisible;
  }

  reload() {
    this.isLoading = true;
    this.fileDataService.refreshCache()
      .subscribe({
        next: (data) => {
          this.syncData = data;
          this.fileCategories = JSON.stringify(data.config.fileCategories, null, 2);
          this.claudeignore = data.config.claudeignore;
          this.stats = data.stats;
          if (this.treemapComponent) {
            this.treemapComponent.reload();
          }
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading data:', error);
          this.isLoading = false;
        }
      });
  }
}
