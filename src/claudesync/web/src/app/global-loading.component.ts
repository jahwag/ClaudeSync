import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LoadingService } from './loading.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-global-loading',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="loading-overlay" *ngIf="isLoading">
      <div class="loading-content">
        <div class="spinner"></div>
        <p class="loading-text">Loading...</p>
      </div>
    </div>
  `,
  styles: [`
    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(255, 255, 255, 0.7);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }

    .loading-content {
      background-color: white;
      padding: 1.5rem;
      border-radius: 0.5rem;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      text-align: center;
    }

    .spinner {
      width: 50px;
      height: 50px;
      border: 5px solid #f3f3f3;
      border-top: 5px solid #2563eb;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .loading-text {
      margin-top: 1rem;
      color: #1e293b;
      font-size: 1rem;
      font-weight: 500;
    }
  `]
})
export class GlobalLoadingComponent implements OnInit, OnDestroy {
  isLoading = false;
  private subscription: Subscription | null = null;

  constructor(private loadingService: LoadingService) {}

  ngOnInit() {
    this.subscription = this.loadingService.loading$.subscribe(
      isLoading => this.isLoading = isLoading
    );
  }

  ngOnDestroy() {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }
}
