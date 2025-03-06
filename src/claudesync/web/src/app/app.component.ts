import {Component, OnInit, ViewChild} from '@angular/core';
import {CommonModule} from '@angular/common';
import {HttpClientModule} from '@angular/common/http';
import {FileDataService, ProjectConfig, SyncData, SyncStats} from './file-data.service';
import {TreemapComponent} from './treemap.component';
import {finalize} from 'rxjs/operators';
import {Project, ProjectDropdownComponent} from './project-dropdown.component';
import {NotificationService} from './notification.service'
import {ToastNotificationsComponent} from './toast-notifications.component';
import { EditableConfigComponent } from './editable-config.component';


@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    TreemapComponent,
    ProjectDropdownComponent,
    ToastNotificationsComponent,
    EditableConfigComponent
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  providers: [FileDataService]
})
export class AppComponent implements OnInit {
  configVisible = false;
  claudeignore = '';
  isLoading = false;
  stats: SyncStats = {
    filesToSync: 0,
    totalSize: '0 B'
  };

  syncData: SyncData | null = null;

  projects: Project[] = [];
  selectedProject: string = '';
  selectedProjectUrl: string = '';
  projectConfig: ProjectConfig | null = null;

  @ViewChild(TreemapComponent) treemapComponent!: TreemapComponent;

  constructor(private fileDataService: FileDataService,
              private notificationService: NotificationService) {
  }

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.isLoading = true;
    this.fileDataService.getProjects()
      .pipe(finalize(() => this.isLoading = false))
      .subscribe({
        next: (response: any) => {
          this.projects = response.projects.sort((a: any, b: any) => a.path.localeCompare(b.path));
          if (response.activeProject) {
            this.selectedProject = response.activeProject;
            this.setSelectedProjectUrl();
            this.loadData();
          } else if (this.projects.length > 0) {
            // If no active project but projects exist, select the first one
            this.selectedProject = this.projects[0].path;
            this.setSelectedProjectUrl();
            this.onProjectChange(this.projects[0].path);
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

    this.setSelectedProjectUrl();

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

  private setSelectedProjectUrl() {
    // Find the project ID from the projects array and set the URL
    const project = this.projects.find(p => p.path === this.selectedProject);
    if (project) {
      this.selectedProjectUrl = `https://claude.ai/project/${project.id}`;
    } else {
      this.selectedProjectUrl = '';
    }
  }

  loadData() {
    this.isLoading = true;
    this.fileDataService.getSyncData()
      .subscribe({
        next: (data) => {
          this.syncData = data;
          this.projectConfig = data.project;
          this.claudeignore = data.claudeignore;
          this.stats = data.stats;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading data:', error);
          this.isLoading = false;
        }
      });
  }

  toggleConfig() {
    this.configVisible = !this.configVisible;
  }

  reload() {
    // Only set isLoading to true if it wasn't already true
    const wasLoading = this.isLoading;
    if (!wasLoading) {
      this.isLoading = true;
    }

    this.fileDataService.refreshCache()
      .subscribe({
        next: (data) => {
          // Create a new object reference to trigger change detection
          this.syncData = {...data};  // Use spread to create a new reference
          this.projectConfig = data.project;
          this.claudeignore = data.claudeignore;
          this.stats = data.stats;

          // Only set isLoading to false if we were the ones who set it to true
          if (!wasLoading) {
            this.isLoading = false;
          }
        },
        error: (error) => {
          console.error('Error loading data:', error);
          if (!wasLoading) {
            this.isLoading = false;
          }
        }
      });
  }

  getProjectConfigAsJson(): string {
    return this.projectConfig
      ? JSON.stringify(this.projectConfig, null, 2)
      : '{}';
  }

  push() {
    this.isLoading = true;
    this.fileDataService.push()
      .pipe(finalize(() => this.isLoading = false))
      .subscribe({
        next: (response) => {
          // Show success notification with the response message
          if (response && response.message) {
            this.notificationService.success(response.message);
          } else {
            this.notificationService.success('Files pushed successfully!');
          }
          this.reload();
        },
        error: (error) => {
          // Show error notification with the error message
          const errorMessage = error.error?.message || 'Failed to push files. Please try again.';
          this.notificationService.error(errorMessage);
          console.error('Error pushing to backend:', error);
        }
      });
  }

  saveProjectConfig(newContent: string) {
    console.debug('Saving project config', newContent.substring(0, 100) + '...');

    this.isLoading = true;
    this.fileDataService.saveProjectConfig(newContent)
      .pipe(finalize(() => this.isLoading = false))
      .subscribe({
        next: () => {
          // Update the local project config
          try {
            this.projectConfig = JSON.parse(newContent);
            this.notificationService.success('Project configuration updated successfully');
            // Trigger a reload to refresh the view
            this.reload();

            // Additional line to ensure treemap gets refreshed
            if (this.treemapComponent) {
              setTimeout(() => this.treemapComponent.updateTreemap(), 100);
            }
          } catch (error) {
            this.notificationService.error('Error parsing updated configuration');
            console.error('JSON parse error:', error);
          }
        },
        error: (error) => {
          // More specific error messages based on status codes
          if (error.status === 400) {
            this.notificationService.error(error.error?.error || 'Invalid configuration format');
          } else if (error.status === 403) {
            this.notificationService.error('Permission denied when saving configuration');
          } else {
            this.notificationService.error('Failed to save project configuration');
          }
          console.error('Configuration save error:', error);
        }
      });
  }

  saveClaudeIgnore(newContent: string) {
    console.debug('Saving project config', newContent.substring(0, 100) + '...');

    this.isLoading = true;
    this.fileDataService.saveClaudeIgnore(newContent)
      .pipe(finalize(() => this.isLoading = false))
      .subscribe({
        next: () => {
          this.claudeignore = newContent;
          this.notificationService.success('.claudeignore updated successfully');
          // Trigger a reload to refresh the view
          this.reload();
        },
        error: (error) => {
          // More specific error messages based on status codes
          if (error.status === 400) {
            this.notificationService.error(error.error?.error || 'Invalid .claudeignore format');
          } else if (error.status === 403) {
            this.notificationService.error('Permission denied when saving .claudeignore');
          } else {
            this.notificationService.error('Failed to save .claudeignore');
          }
          console.error('Claudeignore save error:', error);
        }
      });
  }
}
