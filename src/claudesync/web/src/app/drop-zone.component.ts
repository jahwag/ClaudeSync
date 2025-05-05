// drop-zone.component.ts
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface DroppedFile {
  name: string;
  content: string;
  lastModified: number;
  size: number;
  type: string;
}

@Component({
  selector: 'app-drop-zone',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './drop-zone.component.html',
  styleUrls: ['./drop-zone.component.css']
})
export class DropZoneComponent {
  @Output() filesDropped = new EventEmitter<DroppedFile[]>();
  @Input() showDropIndicator = true;
  @Input() acceptMessage = 'Drag files here to add them to the project';

  isDragging = false;

  // Handle dragover event
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  // Handle dragleave event
  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  // Handle dragenter event
  onDragEnter(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  // Handle drop event
  async onDrop(event: DragEvent): Promise<void> {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    if (!event.dataTransfer?.files.length) {
      return;
    }

    const droppedFiles: DroppedFile[] = [];
    const files = event.dataTransfer.files;

    // Process each dropped file
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const content = await this.readFileContent(file);
        droppedFiles.push({
          name: file.name,
          content: content,
          lastModified: file.lastModified,
          size: file.size,
          type: file.type
        });
      } catch (error) {
        console.error(`Error reading file ${file.name}:`, error);
      }
    }

    if (droppedFiles.length > 0) {
      this.filesDropped.emit(droppedFiles);
    }
  }

  // Read file content as text
  private readFileContent(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = () => {
        resolve(reader.result as string);
      };

      reader.onerror = () => {
        reject(new Error(`Error reading file: ${file.name}`));
      };

      reader.readAsText(file);
    });
  }
}
