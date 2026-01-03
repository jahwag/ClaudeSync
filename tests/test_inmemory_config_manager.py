import unittest
from datetime import datetime, timedelta

from claudesync.configmanager import InMemoryConfigManager


class TestInMemoryConfigManager(unittest.TestCase):
    def test_defaults_are_present(self):
        cfg = InMemoryConfigManager()
        # Should come from BaseConfigManager._get_default_config()
        self.assertEqual(cfg.get("log_level"), "INFO")
        self.assertIsInstance(cfg.get("file_categories"), dict)

    def test_session_key_helpers(self):
        cfg = InMemoryConfigManager()
        expiry = datetime.now() + timedelta(days=1)
        cfg.set_session_key("claude.ai", "sk-ant-1234", expiry)

        providers = cfg.get_providers_with_session_keys()
        self.assertIn("claude.ai", providers)

        cfg.clear_all_session_keys()
        providers_after = cfg.get_providers_with_session_keys()
        self.assertEqual(providers_after, [])

    def test_get_local_path_prefers_explicit_setting(self):
        cfg = InMemoryConfigManager()
        self.assertEqual(cfg.get_local_path(), ".")

        cfg.set("local_path", "/tmp/project", local=True)
        self.assertEqual(cfg.get_local_path(), "/tmp/project")


if __name__ == "__main__":
    unittest.main()

