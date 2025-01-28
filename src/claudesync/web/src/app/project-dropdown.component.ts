import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface Project {
  id: string;
  path: string;
  url?: string;
  linked: boolean;
}

@Component({
  selector: 'app-project-dropdown',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './project-dropdown.component.html',
  styleUrls: ['./project-dropdown.component.css']
})
export class ProjectDropdownComponent {
  @Input() projects: Project[] = [];
  @Input() selectedProject: string = '';
  @Input() selectedProjectUrl: string = '';
  @Output() projectChange = new EventEmitter<string>();

  onProjectChange(path: string) {
    this.projectChange.emit(path);
  }

  // Helper method to get display text for project
  getProjectDisplayText(project: Project): string {
    return `${project.path}${!project.linked ? ' (Unlinked)' : ''}`;
  }

  selectedProjectIsLinked(): boolean {
    return this.projects.find(p => p.path === this.selectedProject)?.linked ?? false
  }
}
