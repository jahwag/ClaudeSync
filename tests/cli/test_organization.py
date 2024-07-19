import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from claudesync.cli.main import cli
from claudesync.exceptions import ConfigurationError, ProviderError


class TestOrganizationCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch("claudesync.cli.organization.validate_and_get_provider")
    def test_organization_ls(self, mock_validate_and_get_provider):
        # Mock the provider
        mock_provider = MagicMock()
        mock_provider.get_organizations.return_value = [
            {"id": "org1", "name": "Organization 1"},
            {"id": "org2", "name": "Organization 2"},
        ]
        mock_validate_and_get_provider.return_value = mock_provider

        # Test successful listing
        result = self.runner.invoke(cli, ["organization", "ls"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Organization 1", result.output)
        self.assertIn("Organization 2", result.output)

        # Test empty list
        mock_provider.get_organizations.return_value = []
        result = self.runner.invoke(cli, ["organization", "ls"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No organizations found.", result.output)

        # Test error handling
        mock_validate_and_get_provider.side_effect = ConfigurationError(
            "Configuration error"
        )
        result = self.runner.invoke(cli, ["organization", "ls"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Error: Configuration error", result.output)

    @patch("claudesync.cli.organization.validate_and_get_provider")
    @patch("claudesync.cli.organization.click.prompt")
    def test_organization_select(self, mock_prompt, mock_validate_and_get_provider):
        # Mock the provider
        mock_provider = MagicMock()
        mock_provider.get_organizations.return_value = [
            {"id": "org1", "name": "Organization 1"},
            {"id": "org2", "name": "Organization 2"},
        ]
        mock_validate_and_get_provider.return_value = mock_provider

        # Mock user input
        mock_prompt.return_value = 1

        # Test successful selection
        result = self.runner.invoke(cli, ["organization", "select"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Selected organization: Organization 1", result.output)

        # Test invalid selection
        mock_prompt.return_value = 3
        result = self.runner.invoke(cli, ["organization", "select"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Invalid selection. Please try again.", result.output)

        # Test empty list
        mock_provider.get_organizations.return_value = []
        result = self.runner.invoke(cli, ["organization", "select"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No organizations found.", result.output)

        # Test error handling
        mock_validate_and_get_provider.side_effect = ProviderError("Provider error")
        result = self.runner.invoke(cli, ["organization", "select"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Error: Provider error", result.output)


if __name__ == "__main__":
    unittest.main()
