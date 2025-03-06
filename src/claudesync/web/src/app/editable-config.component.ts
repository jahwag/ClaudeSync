import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MonacoEditorModule } from 'ngx-monaco-editor-v2';

@Component({
  selector: 'app-editable-config',
  standalone: true,
  imports: [CommonModule, FormsModule, MonacoEditorModule],
  template: `
    <div class="editable-config-container">
      <!-- Read mode -->
      <div *ngIf="!editMode" class="code-block-wrapper">
        <pre
          class="code-block editable-indicator"
          (click)="enableEditMode()">{{content}}</pre>

        <button
          class="edit-button"
          (click)="enableEditMode($event)">
          <svg class="icon" viewBox="0 0 24 24">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
          Edit
        </button>
      </div>

      <!-- Edit mode -->
      <div *ngIf="editMode" class="editor-container">
        <div class="editor-header">
          <span class="edit-mode-indicator">Editing {{ typeLabel }}</span>
        </div>

        <ngx-monaco-editor
          *ngIf="editMode"
          class="monaco-editor"
          [options]="editorOptions"
          [ngModel]="content"
          (ngModelChange)="editorContent = $event"
          (onInit)="onEditorInit($event)"
          style="height: 400px">
        </ngx-monaco-editor>

        <div class="editor-actions">
          <button
            class="btn btn-primary"
            [disabled]="!!validationError"
            (click)="saveChanges()">
            Save
          </button>
          <button class="btn btn-secondary" (click)="cancelEdit()">
            Cancel
          </button>
        </div>

        <div *ngIf="validationError" class="validation-error">
          <svg class="error-icon" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {{validationError}}
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./editable-config.component.css']
})
export class EditableConfigComponent implements OnInit {
  @Input() content: string = '';
  @Input() type: 'project_config' | 'claudeignore' = 'claudeignore';
  @Output() contentChanged = new EventEmitter<string>();

  editMode = false;
  editorContent = '';
  validationError = '';
  editor: any = null;

  get typeLabel(): string {
    return this.type === 'project_config' ? 'Project Configuration' : '.claudeignore';
  }

  editorOptions = {
    theme: 'vs',
    language: this.type === 'project_config' ? 'json' : 'plaintext',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    lineNumbers: 'on',
    wordWrap: 'on',
    renderWhitespace: 'boundary',
    renderControlCharacters: true
  };

  ngOnInit() {
    this.editorContent = this.content;
    // Set the correct language based on the type
    this.editorOptions.language = this.type === 'project_config' ? 'json' : 'plaintext';
  }

  onEditorInit(editor: any) {
    this.editor = editor;
    // Set content in the editor directly as a backup
    editor.setValue(this.content);
    // Add change event listener
    editor.onDidChangeModelContent(() => {
      this.editorContent = editor.getValue();
      this.validateContent();
    });
  }

  enableEditMode(event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    this.editMode = true;
    this.editorContent = this.content;
    this.validationError = '';
  }

  validateContent() {
    if (this.type === 'project_config') {
      try {
        JSON.parse(this.editorContent);
        this.validationError = '';
      } catch (e: any) {
        this.validationError = `Invalid JSON: ${e.message}`;
      }
    }
    // Add any .claudeignore validation here if needed
    return !this.validationError;
  }

  saveChanges() {
    if (this.validateContent()) {
      this.contentChanged.emit(this.editorContent);
      this.editMode = false;
    }
  }

  cancelEdit() {
    this.editMode = false;
    this.validationError = '';
  }
}
