import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { FileDataService, SyncStats, FileConfig } from './file-data.service';
import {TreemapComponent} from './treemap.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule, HttpClientModule, TreemapComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
  providers: [FileDataService]
})
export class AppComponent implements OnInit {
  configVisible = false;
  fileCategories = '';
  claudeignore = '';
  stats: SyncStats = {
    totalFiles: 0,
    filesToSync: 0,
    totalSize: '0 B'
  };

  constructor(private fileDataService: FileDataService) {}

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.fileDataService.getFileConfig().subscribe({
      next: (config: FileConfig) => {
        this.fileCategories = JSON.stringify(config.fileCategories, null, 2);
        this.claudeignore = config.claudeignore;
      },
      error: (error) => console.error('Error loading config:', error)
    });

    this.fileDataService.getStats().subscribe({
      next: (stats: SyncStats) => {
        this.stats = stats;
      },
      error: (error) => console.error('Error loading stats:', error)
    });
  }

  toggleConfig() {
    this.configVisible = !this.configVisible;
  }

  reload() {
    this.loadData();
  }
}
