import pytest
from unittest.mock import patch, MagicMock, call
from click.testing import CliRunner
from claudesync.cli.project import sync
from claudesync.exceptions import ProviderError


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "active_organization_id": "org123",
        "active_project_id": "proj456",
        "active_project_name": "MainProject",
        "local_path": "/path/to/project",
        "submodule_detect_filenames": ["pom.xml", "build.gradle"],
    }.get(key, default)
    return config


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def mock_sync_manager():
    return MagicMock()


@pytest.fixture
def mock_get_local_files():
    with patch("claudesync.cli.project.get_local_files") as mock:
        yield mock


@pytest.fixture
def mock_detect_submodules():
    with patch("claudesync.cli.project.detect_submodules") as mock:
        yield mock


class TestProjectCLI:
    @patch("claudesync.cli.project.validate_and_get_provider")
    @patch("claudesync.cli.project.SyncManager")
    @patch("os.path.abspath")
    @patch("os.path.join")
    @patch("os.makedirs")
    def test_project_sync(
        self,
        mock_makedirs,
        mock_path_join,
        mock_path_abspath,
        mock_sync_manager_class,
        mock_validate_provider,
        mock_config,
        mock_provider,
        mock_sync_manager,
        mock_get_local_files,
        mock_detect_submodules,
    ):
        # Setup
        runner = CliRunner()
        mock_validate_provider.return_value = mock_provider
        mock_sync_manager_class.return_value = mock_sync_manager

        mock_provider.get_projects.return_value = [
            {"id": "proj456", "name": "MainProject"},
            {"id": "sub789", "name": "MainProject-SubModule-SubA"},
        ]
        mock_provider.list_files.side_effect = [
            [
                {
                    "uuid": "file1",
                    "file_name": "main.py",
                    "content": "print('main')",
                    "created_at": "2023-01-01T00:00:00Z",
                }
            ],
            [
                {
                    "uuid": "file2",
                    "file_name": "sub.py",
                    "content": "print('sub')",
                    "created_at": "2023-01-01T00:00:00Z",
                }
            ],
        ]

        mock_get_local_files.side_effect = [{"main.py": "hash1"}, {"sub.py": "hash2"}]

        mock_detect_submodules.return_value = [("SubA", "pom.xml")]

        mock_path_abspath.side_effect = lambda x: x
        mock_path_join.side_effect = lambda *args: "/".join(args)

        # Execute
        result = runner.invoke(sync, obj=mock_config)

        # Assert
        assert (
            result.exit_code == 0
        ), f"Exit code was {result.exit_code}, expected 0. Exception: {result.exception}"
        assert "Main project 'MainProject' synced successfully." in result.output
        assert "Syncing submodule 'SubA'..." in result.output
        assert "Submodule 'SubA' synced successfully." in result.output
        assert (
            "Project sync completed successfully, including available submodules."
            in result.output
        )

        # Verify method calls
        mock_validate_provider.assert_called_once_with(
            mock_config, require_project=True
        )
        mock_provider.get_projects.assert_called_once_with(
            "org123", include_archived=False
        )
        mock_detect_submodules.assert_called_once_with(
            "/path/to/project", ["pom.xml", "build.gradle"]
        )

        assert mock_provider.list_files.call_count == 2
        mock_provider.list_files.assert_has_calls(
            [call("org123", "proj456"), call("org123", "sub789")]
        )

        assert mock_get_local_files.call_count == 2
        mock_get_local_files.assert_has_calls(
            [call("/path/to/project", None), call("/path/to/project/SubA", None)]
        )

        assert mock_sync_manager.sync.call_count == 2
        mock_sync_manager.sync.assert_has_calls(
            [
                call(
                    {"main.py": "hash1"},
                    [
                        {
                            "uuid": "file1",
                            "file_name": "main.py",
                            "content": "print('main')",
                            "created_at": "2023-01-01T00:00:00Z",
                        }
                    ],
                ),
                call(
                    {"sub.py": "hash2"},
                    [
                        {
                            "uuid": "file2",
                            "file_name": "sub.py",
                            "content": "print('sub')",
                            "created_at": "2023-01-01T00:00:00Z",
                        }
                    ],
                ),
            ]
        )

    @patch("claudesync.cli.project.validate_and_get_provider")
    def test_project_sync_no_local_path(self, mock_validate_provider, mock_config):
        runner = CliRunner()
        mock_config.get.side_effect = lambda key, default=None: (
            None if key == "local_path" else default
        )
        mock_validate_provider.return_value = MagicMock()

        result = runner.invoke(sync, obj=mock_config)

        assert result.exit_code == 0
        assert (
            "No local path set. Please select or create a project first."
            in result.output
        )

    @patch("claudesync.cli.project.validate_and_get_provider")
    def test_project_sync_provider_error(self, mock_validate_provider, mock_config):
        runner = CliRunner()
        mock_validate_provider.side_effect = ProviderError("API Error")

        result = runner.invoke(sync, obj=mock_config)

        assert result.exit_code == 0
        assert "Error: API Error" in result.output

    @patch("claudesync.cli.project.validate_and_get_provider")
    @patch("claudesync.cli.project.SyncManager")
    def test_project_sync_no_submodules(
        self,
        mock_sync_manager_class,
        mock_validate_provider,
        mock_config,
        mock_provider,
        mock_sync_manager,
        mock_get_local_files,
        mock_detect_submodules,
    ):
        runner = CliRunner()
        mock_validate_provider.return_value = mock_provider
        mock_sync_manager_class.return_value = mock_sync_manager

        mock_provider.get_projects.return_value = [
            {"id": "proj456", "name": "MainProject"}
        ]
        mock_provider.list_files.return_value = [
            {
                "uuid": "file1",
                "file_name": "main.py",
                "content": "print('main')",
                "created_at": "2023-01-01T00:00:00Z",
            }
        ]
        mock_get_local_files.return_value = {"main.py": "hash1"}
        mock_detect_submodules.return_value = []

        result = runner.invoke(sync, obj=mock_config)

        assert result.exit_code == 0
        assert "Main project 'MainProject' synced successfully." in result.output
        assert (
            "Project sync completed successfully, including available submodules."
            in result.output
        )
        assert "Syncing submodule" not in result.output

        mock_sync_manager.sync.assert_called_once()

    @patch("claudesync.cli.project.validate_and_get_provider")
    @patch("claudesync.cli.project.SyncManager")
    def test_project_sync_with_category(
        self,
        mock_sync_manager_class,
        mock_validate_provider,
        mock_config,
        mock_provider,
        mock_sync_manager,
        mock_get_local_files,
        mock_detect_submodules,
    ):
        runner = CliRunner()
        mock_validate_provider.return_value = mock_provider
        mock_sync_manager_class.return_value = mock_sync_manager

        mock_provider.get_projects.return_value = [
            {"id": "proj456", "name": "MainProject"}
        ]
        mock_provider.list_files.return_value = [
            {
                "uuid": "file1",
                "file_name": "main.py",
                "content": "print('main')",
                "created_at": "2023-01-01T00:00:00Z",
            }
        ]
        mock_get_local_files.return_value = {"main.py": "hash1"}
        mock_detect_submodules.return_value = []

        result = runner.invoke(sync, ["--category", "production_code"], obj=mock_config)

        assert result.exit_code == 0
        assert "Main project 'MainProject' synced successfully." in result.output

        mock_get_local_files.assert_called_once_with(
            "/path/to/project", "production_code"
        )
        mock_sync_manager.sync.assert_called_once()

    @patch("claudesync.cli.project.validate_and_get_provider")
    @patch("claudesync.cli.project.SyncManager")
    def test_project_sync_with_invalid_category(
        self,
        mock_sync_manager_class,
        mock_validate_provider,
        mock_config,
        mock_provider,
        mock_sync_manager,
        mock_get_local_files,
        mock_detect_submodules,
    ):
        runner = CliRunner()
        mock_validate_provider.return_value = mock_provider
        mock_sync_manager_class.return_value = mock_sync_manager

        mock_get_local_files.side_effect = ValueError(
            "Invalid category: invalid_category"
        )

        result = runner.invoke(
            sync, ["--category", "invalid_category"], obj=mock_config
        )

        assert result.exit_code == 1
        assert "Invalid category: invalid_category" in result.exception.args[0]

        mock_sync_manager.sync.assert_not_called()
