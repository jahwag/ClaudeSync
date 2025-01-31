import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SelectedNode } from './treemap.types';

interface NodeAction {
  id: string;
  label: string;
  icon: string;
  description: string;
}

@Component({
  selector: 'app-node-actions-menu',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './node-actions-menu.component.html',
  styleUrls: ['./node-actions-menu.component.css']
})
export class NodeActionsMenuComponent {
  @Input() node: SelectedNode | null = null;
  @Output() actionTriggered = new EventEmitter<string>();

  isOpen = false;

  actions: NodeAction[] = [
    {
      id: 'copy',
      label: 'Copy Path',
      icon: '📋',
      description: 'Copy file or directory path to clipboard'
    },
    {
      id: 'addToIncludes',
      label: 'Add to Includes',
      icon: '➕',
      description: 'Add this path to project includes'
    },
    {
      id: 'removeFromIncludes',
      label: 'Remove from Includes',
      icon: '❌',
      description: 'Remove this path from project includes'
    },
    {
      id: 'addToExcludes',
      label: 'Add to Excludes',
      icon: '🚫',
      description: 'Add this path to project excludes'
    },
    {
      id: 'removeFromExcludes',
      label: 'Remove from Excludes',
      icon: '✅',
      description: 'Remove this path from project excludes'
    },
    {
      id: 'clear',
      label: 'Clear Selection',
      icon: '🔄',
      description: 'Clear current selection'
    }
  ];

  toggleMenu(): void {
    this.isOpen = !this.isOpen;
  }

  handleAction(actionId: string): void {
    this.actionTriggered.emit(actionId);
    this.isOpen = false;
  }

  closeMenu(event: MouseEvent): void {
    // Close menu if clicking outside
    if (!(event.target as HTMLElement).closest('.actions-menu')) {
      this.isOpen = false;
    }
  }
}
