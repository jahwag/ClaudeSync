import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface Notification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  duration?: number;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  // Private BehaviorSubject to hold notifications
  private notificationsSubject = new BehaviorSubject<Notification[]>([]);

  // Public observable that components can subscribe to
  notifications$: Observable<Notification[]> = this.notificationsSubject.asObservable();

  constructor() {}

  // Show a new notification
  show(message: string, type: Notification['type'] = 'info', duration: number = 5000): void {
    // Create new notification
    const notification: Notification = {
      id: this.generateId(),
      message,
      type,
      duration
    };

    // Add to current notifications
    const currentNotifications = this.notificationsSubject.value;
    this.notificationsSubject.next([...currentNotifications, notification]);

    // Auto-dismiss if duration is provided
    if (duration > 0) {
      setTimeout(() => {
        this.dismiss(notification.id);
      }, duration);
    }
  }

  // Show success notification
  success(message: string, duration: number = 5000): void {
    this.show(message, 'success', duration);
  }

  // Show error notification
  error(message: string, duration: number = 8000): void {
    this.show(message, 'error', duration);
  }

  // Show info notification
  info(message: string, duration: number = 5000): void {
    this.show(message, 'info', duration);
  }

  // Show warning notification
  warning(message: string, duration: number = 6000): void {
    this.show(message, 'warning', duration);
  }

  // Dismiss a specific notification
  dismiss(id: string): void {
    const currentNotifications = this.notificationsSubject.value;
    this.notificationsSubject.next(
      currentNotifications.filter(notification => notification.id !== id)
    );
  }

  // Clear all notifications
  clear(): void {
    this.notificationsSubject.next([]);
  }

  // Generate unique ID for notifications
  private generateId(): string {
    return '_' + Math.random().toString(36).substr(2, 9);
  }
}
