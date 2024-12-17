import {Component, OnInit, ViewChild} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { FileDataService, SyncStats, FileConfig } from './file-data.service';
import {TreemapComponent} from './treemap.component';
import {finalize} from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule, TreemapComponent],
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

  @ViewChild(TreemapComponent) treemapComponent!: TreemapComponent;

  constructor(private fileDataService: FileDataService) {}

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.isLoading = true;
    this.fileDataService.getSyncData()
      .subscribe({
        next: (data) => {
          this.fileCategories = JSON.stringify(data.config.fileCategories, null, 2);
          this.claudeignore = data.config.claudeignore;
          this.stats = data.stats;
          this.isLoading = false;
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
    this.fileDataService.refreshCache();
    if (this.treemapComponent) {
      this.treemapComponent.reload();
    }
  }
}
