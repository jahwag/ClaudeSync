import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, tap } from 'rxjs/operators';

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
  private cachedData: SyncData | null = null;

  constructor(private http: HttpClient) {}

  private getSyncDataFromApi(): Observable<SyncData> {
    return this.http.get<SyncData>(`${this.baseUrl}/sync-data`).pipe(
      tap(data => {
        this.cachedData = data;
        console.debug('Cached sync data updated');
      })
    );
  }

  getSyncData(): Observable<SyncData> {
    if (this.cachedData) {
      return of(this.cachedData);
    }
    return this.getSyncDataFromApi();
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

  refreshCache(): Observable<SyncData> {
    this.cachedData = null;
    return this.getSyncData();
  }

  clearCache(): void {
    this.cachedData = null;
  }

  // File content is not cached as it's requested on-demand
  getFileContent(filePath: string): Observable<FileContentResponse> {
    return this.http.get<FileContentResponse>(`${this.baseUrl}/file-content`, {
      params: { path: filePath }
    });
  }
}
