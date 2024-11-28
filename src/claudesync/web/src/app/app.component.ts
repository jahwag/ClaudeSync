import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  configVisible = false;
  fileCategories = JSON.stringify({
    "file_categories": {
      "main": {
        "description": "Active Category",
        "patterns": [
          "app.py",
          "src/index.html",
          "src/main.ts",
          "src/styles.css"
        ]
      }
    }
  }, null, 2);

  claudeignore = `node_modules/
.venv/
.angular/
.git/
.idea/
.vscode/
*.zip
pkg/`;

  stats = {
    totalFiles: 127,
    filesToSync: 43,
    totalSize: '2.4 MB'
  };

  ngOnInit() {
    // Initialize component
  }

  toggleConfig() {
    this.configVisible = !this.configVisible;
  }

  reload() {
    // Implement reload logic
    console.log('Reloading visualization...');
  }
}
