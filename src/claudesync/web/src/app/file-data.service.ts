import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {map} from 'rxjs/operators';

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
  treemap: any; // Using any for treemap data as it's a complex nested structure
}

@Injectable({
  providedIn: 'root'
})
export class FileDataService {
  private baseUrl = 'http://localhost:4201/api';

  constructor(private http: HttpClient) {}

  getSyncData(): Observable<SyncData> {
    return this.http.get<SyncData>(`${this.baseUrl}/sync-data`);
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

  getFileContent(filePath: string): Observable<FileContentResponse> {
    return this.http.get<FileContentResponse>(`${this.baseUrl}/file-content`, {
      params: { path: filePath }
    });
  }
}
