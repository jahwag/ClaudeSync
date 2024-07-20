import json
from pathlib import Path


class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".claudesync"
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()

    def _load_config(self):
        if not self.config_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            return {
                "log_level": "INFO",
                "upload_delay": 0.5,
                "max_file_size": 32 * 1024,  # Default 32 KB
            }
        with open(self.config_file, "r") as f:
            config = json.load(f)
            if "log_level" not in config:
                config["log_level"] = "INFO"
            if "upload_delay" not in config:
                config["upload_delay"] = 0.5
            if "max_file_size" not in config:
                config["max_file_size"] = 32 * 1024  # Default 32 KB
            return config

    def _save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self._save_config()
