import {Component, OnInit, ViewChild} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { FileDataService, SyncStats, FileConfig } from './file-data.service';
import {TreemapComponent} from './treemap.component';

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

    // Create an array of observables for parallel execution
    const requests = [
      this.fileDataService.getFileConfig(),
      this.fileDataService.getStats()
    ];

    // Execute requests in parallel
    // @ts-ignore
    Promise.all(requests.map(obs => obs.toPromise()))
      .then(([config, stats]) => {
        // @ts-ignore
        this.fileCategories = JSON.stringify(config.fileCategories, null, 2);
        // @ts-ignore
        this.claudeignore = config.claudeignore;
        // @ts-ignore
        this.stats = stats;
      })
      .catch(error => console.error('Error loading data:', error))
      .finally(() => {
        this.isLoading = false;
      });
  }

  toggleConfig() {
    this.configVisible = !this.configVisible;
  }

  reload() {
    this.loadData();
    if (this.treemapComponent) {
      this.treemapComponent.reload();
    }
  }
}
