import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from claudesync.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".claudesync"
        self.config_file = self.config_dir / "config.json"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("pathlib.Path.home")
    def test_init_existing_config(self, mock_home):
        mock_home.return_value = Path(self.temp_dir)
        self.config_dir.mkdir(parents=True)
        with open(self.config_file, "w") as f:
            json.dump({"existing_key": "value"}, f)

        config = ConfigManager()
        self.assertEqual(config.get("existing_key"), "value")
        self.assertEqual(config.get("log_level"), "INFO")
        self.assertEqual(config.get("upload_delay"), 0.5)

    @patch("pathlib.Path.home")
    def test_get_existing_key(self, mock_home):
        mock_home.return_value = Path(self.temp_dir)
        config = ConfigManager()
        config.set("test_key", "test_value")
        self.assertEqual(config.get("test_key"), "test_value")

    @patch("pathlib.Path.home")
    def test_get_non_existing_key(self, mock_home):
        mock_home.return_value = Path(self.temp_dir)
        config = ConfigManager()
        self.assertIsNone(config.get("non_existing_key"))
        self.assertEqual(config.get("non_existing_key", "default"), "default")

    @patch("pathlib.Path.home")
    def test_set_and_save(self, mock_home):
        mock_home.return_value = Path(self.temp_dir)
        config = ConfigManager()
        config.set("new_key", "new_value")

        # Check if the new value is in the instance
        self.assertEqual(config.get("new_key"), "new_value")

        # Check if the new value was saved to the file
        with open(self.config_file, "r") as f:
            saved_config = json.load(f)
        self.assertEqual(saved_config["new_key"], "new_value")

    @patch("pathlib.Path.home")
    def test_update_existing_value(self, mock_home):
        mock_home.return_value = Path(self.temp_dir)
        config = ConfigManager()
        config.set("update_key", "original_value")
        config.set("update_key", "updated_value")

        self.assertEqual(config.get("update_key"), "updated_value")

        with open(self.config_file, "r") as f:
            saved_config = json.load(f)
        self.assertEqual(saved_config["update_key"], "updated_value")


if __name__ == "__main__":
    unittest.main()
