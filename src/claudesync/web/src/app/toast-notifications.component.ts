import { Component, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService, Notification } from './notification.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-toast-notifications',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './toast-notifications.component.html',
  styleUrls: ['./toast-notifications.component.css']
})
export class ToastNotificationsComponent implements OnDestroy {
  notifications: Notification[] = [];
  private subscription: Subscription;

  constructor(private notificationService: NotificationService) {
    // Subscribe to notifications
    this.subscription = this.notificationService.notifications$.subscribe(
      notifications => this.notifications = notifications
    );
  }

  ngOnDestroy() {
    // Clean up subscription
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }

  dismiss(id: string) {
    this.notificationService.dismiss(id);
  }

  // Helper method to get appropriate CSS class based on notification type
  getTypeClass(type: string): string {
    switch (type) {
      case 'success':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'info':
        return 'bg-blue-500';
      case 'warning':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  }

  // Method to get icon class based on notification type
  getIconClass(type: string): string {
    switch (type) {
      case 'success':
        return 'text-green-500';
      case 'error':
        return 'text-red-500';
      case 'info':
        return 'text-blue-500';
      case 'warning':
        return 'text-yellow-500';
      default:
        return 'text-gray-500';
    }
  }

  // Method to track notifications by their ID for ngFor optimization
  trackById(index: number, notification: Notification): string {
    return notification.id;
  }
}
