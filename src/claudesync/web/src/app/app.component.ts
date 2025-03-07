import {Component, OnInit, ViewChild} from '@angular/core';
import {CommonModule} from '@angular/common';
import {HttpClientModule} from '@angular/common/http';
import {FileDataService, ProjectConfig, SyncData, SyncStats} from './file-data.service';
import {TreemapComponent} from './treemap.component';
import {Project, ProjectDropdownComponent} from './project-dropdown.component';
import {NotificationService} from './notification.service'
import {ToastNotificationsComponent} from './toast-notifications.component';
import {EditableConfigComponent} from './editable-config.component';
import {GlobalLoadingComponent} from './global-loading.component';



@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    TreemapComponent,
    ProjectDropdownComponent,
    ToastNotificationsComponent,
    EditableConfigComponent,
    GlobalLoadingComponent
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  providers: [FileDataService]
})
export class AppComponent implements OnInit {
  configVisible = false;
  claudeignore = '';
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
    this.fileDataService.getProjects()
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
    this.fileDataService.getSyncData()
      .subscribe({
        next: (data) => {
          this.syncData = data;
          this.projectConfig = data.project;
          this.claudeignore = data.claudeignore;
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
    this.fileDataService.refreshCache()
      .subscribe({
        next: (data) => {
          // Create a new object reference to trigger change detection
          this.syncData = {...data};  // Use spread to create a new reference
          this.projectConfig = data.project;
          this.claudeignore = data.claudeignore;
          this.stats = data.stats;
        },
        error: (error) => {
          console.error('Error loading data:', error);
        }
      });
  }

  getProjectConfigAsJson(): string {
    return this.projectConfig
      ? JSON.stringify(this.projectConfig, null, 2)
      : '{}';
  }

  push() {
    this.fileDataService.push()
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

    this.fileDataService.saveProjectConfig(newContent)
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

    this.fileDataService.saveClaudeIgnore(newContent)
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
