import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-file-preview',
  standalone: true,
  imports: [CommonModule],
  templateUrl: 'file-preview.component.html',
  styleUrls: ['file-preview.component.css']
})
export class FilePreviewComponent {
  @Input() content: string | null = null;
  @Input() error: string | null = null;
  @Input() isLoading = false;
}
