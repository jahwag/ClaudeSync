import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable, of} from 'rxjs';
import {map, tap} from 'rxjs/operators';
import {Project} from './project-dropdown.component';
import {LoadingService} from './loading.service';
import {DroppedFile} from './drop-zone.component';

export interface SyncStats {
  filesToSync: number;
  totalSize: string;
}

export interface ProjectConfig {
  name: string;
  description: string;
  includes: string[];
  excludes: string[];
}

export interface TreemapData {
  labels: string[];
  parents: string[];
  values: number[];
  ids: string[];
}

export interface FileContentResponse {
  content: string;
  error?: string;
}

export interface SyncData {
  claudeignore: string;
  project: ProjectConfig;
  stats: SyncStats;
  treemap: any;
}

@Injectable({
  providedIn: 'root'
})
export class FileDataService {
  private baseUrl = 'http://localhost:4201/api';
  private cachedData: SyncData | null = null;

  constructor(private http: HttpClient, private loadingService: LoadingService) {}

  private getSyncDataFromApi(): Observable<SyncData> {
    return this.loadingService.withLoading(
      this.http.get<SyncData>(`${this.baseUrl}/sync-data`).pipe(
        tap(data => {
          this.cachedData = data;
          console.debug('Cached sync data updated');
        })
      ));
  }

  getSyncData(): Observable<SyncData> {
    if (this.cachedData) {
      return of(this.cachedData);
    }
    return this.getSyncDataFromApi();
  }

  getProjectConfig(): Observable<ProjectConfig> {
    return this.getSyncData().pipe(
      map(data => data.project)
    );
  }

  getClaudeIgnore(): Observable<string> {
    return this.getSyncData().pipe(
      map(data => data.claudeignore)
    );
  }

  getStats(): Observable<SyncStats> {
    return this.getSyncData().pipe(
      map(data => data.stats)
    );
  }

  getTreemapData(): Observable<any> {
    return this.getSyncData().pipe(
      map(data => data.treemap)
    );
  }

  refreshCache(): Observable<SyncData> {
    this.clearCache();
    return this.getSyncData();
  }

  clearCache(): void {
    this.cachedData = null;
    console.debug('Cache cleared');
  }

  getFileContent(filePath: string): Observable<FileContentResponse> {
    return this.loadingService.withLoading(
      this.http.get<FileContentResponse>(`${this.baseUrl}/file-content`, {
        params: { path: filePath }
      })
    );
  }

  getProjects(): Observable<Project[]> {
    return this.loadingService.withLoading(
      this.http.get<Project[]>(`${this.baseUrl}/projects`)
    );
  }

  setActiveProject(projectPath: string): Observable<any> {
    return this.loadingService.withLoading(
      this.http.post(`${this.baseUrl}/set-active-project`, { path: projectPath }).pipe(
        tap(() => this.clearCache())
      )
    );
  }

  updateConfigIncrementally(config: { action: string, pattern: string }): Observable<any> {
    return this.loadingService.withLoading(
      this.http.post(`${this.baseUrl}/update-config-incrementally`, config)
    );
  }

  push(): Observable<any> {
    return this.loadingService.withLoading(
      this.http.post(`${this.baseUrl}/push`, {})
    );
  }

  /**
   * Saves project configuration changes to the backend
   * @param content The updated project configuration JSON string
   * @returns Observable of the API response
   */
  saveProjectConfig(content: string): Observable<any> {
    return this.loadingService.withLoading(
      this.http.post(`${this.baseUrl}/replace-project-config`, { content }).pipe(
        tap(() => this.clearCache())
      )
    );
  }

  /**
   * Saves .claudeignore changes to the backend
   * @param content The updated .claudeignore content
   * @returns Observable of the API response
   */
  saveClaudeIgnore(content: string): Observable<any> {
    return this.loadingService.withLoading(
      this.http.post(`${this.baseUrl}/save-claudeignore`, { content }).pipe(
        tap(() => this.clearCache())
      )
    );
  }

  resolveDroppedFiles(files: DroppedFile[]): Observable<any> {
    return this.loadingService.withLoading(
      this.http.post(`${this.baseUrl}/resolve-dropped-files`, { files })
    );
  }
}
