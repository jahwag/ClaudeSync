import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, ReplaySubject } from 'rxjs';
import {map, shareReplay, switchMap, tap} from 'rxjs/operators';

export interface SyncStats {
  filesToSync: number;
  totalSize: string;
}

export interface FileConfig {
  fileCategories: {
    [key: string]: {
      description: string;
      patterns: string[];
    };
  };
  claudeignore: string;
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
  config: FileConfig;
  stats: SyncStats;
  treemap: any;
}

@Injectable({
  providedIn: 'root'
})
export class FileDataService {
  private baseUrl = 'http://localhost:4201/api';
  private cache$: Observable<SyncData> | null = null;
  private cacheRefreshTrigger = new ReplaySubject<void>(1);

  constructor(private http: HttpClient) {}

  private getSyncDataFromApi(): Observable<SyncData> {
    return this.http.get<SyncData>(`${this.baseUrl}/sync-data`);
  }

  getSyncData(): Observable<SyncData> {
    // Initialize cache if it doesn't exist
    if (!this.cache$) {
      this.cache$ = this.cacheRefreshTrigger.pipe(
        // Switch to new API call when refresh is triggered
        switchMap(() => this.getSyncDataFromApi()),
        // Log cache refresh for debugging
        tap(() => console.debug('Refreshing sync data cache')),
        // Cache the last emitted value and share it between subscribers
        shareReplay(1)
      );

      // Trigger initial load
      this.refreshCache();
    }

    // Assert that cache$ is not null since we just initialized it if it was
    return this.cache$ as Observable<SyncData>;
  }

  // Helper methods to extract specific parts of the sync data
  getFileConfig(): Observable<FileConfig> {
    return this.getSyncData().pipe(
      map(data => data.config)
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

  refreshCache(): void {
    this.cacheRefreshTrigger.next();
  }

  getFileContent(filePath: string): Observable<FileContentResponse> {
    // File content is not cached as it's requested on-demand
    return this.http.get<FileContentResponse>(`${this.baseUrl}/file-content`, {
      params: { path: filePath }
    });
  }

  // Call this method to clear the cache if needed
  clearCache(): void {
    this.cache$ = null;
  }
}
