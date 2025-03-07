import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LoadingService {
  private loadingSubject = new BehaviorSubject<boolean>(false);

  // Public observable that components can subscribe to
  loading$: Observable<boolean> = this.loadingSubject.asObservable();

  constructor() {}

  // Show the loading indicator
  show(): void {
    this.loadingSubject.next(true);
  }

  // Hide the loading indicator
  hide(): void {
    this.loadingSubject.next(false);
  }

  // Utility method for wrapping async operations
  withLoading<T>(observable: Observable<T>): Observable<T> {
    return new Observable<T>(observer => {
      this.show();
      return observable.subscribe({
        next: (value) => {
          observer.next(value);
        },
        error: (error) => {
          this.hide();
          observer.error(error);
        },
        complete: () => {
          this.hide();
          observer.complete();
        }
      });
    });
  }
}
