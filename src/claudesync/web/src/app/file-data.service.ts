import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SyncStats {
  totalFiles: number;
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

@Injectable({
  providedIn: 'root'
})
export class FileDataService {
  private baseUrl = 'http://localhost:4201/api';

  constructor(private http: HttpClient) {}

  getFileConfig(): Observable<FileConfig> {
    return this.http.get<FileConfig>(`${this.baseUrl}/config`);
  }

  getStats(): Observable<SyncStats> {
    return this.http.get<SyncStats>(`${this.baseUrl}/stats`);
  }

  getTreemapData(): Observable<TreemapData> {
    return this.http.get<TreemapData>(`${this.baseUrl}/treemap`);
  }

  getFileContent(filePath: string): Observable<FileContentResponse> {
    return this.http.get<FileContentResponse>(
      `${this.baseUrl}/file-content?path=${encodeURIComponent(filePath)}`
    );
  }
}
