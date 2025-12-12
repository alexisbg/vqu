import json

import pytest
from pytest_mock import MockerFixture

from vqu.json_config_file import load_projects_from_json


class TestLoadProjectsFromJson:
    """Unit tests for the load_projects_from_json function."""

    def test_load_projects_from_json_not_found(self) -> None:
        """FileNotFoundError is raised when the file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_projects_from_json("/nonexistent/path/.vqu.json")

    def test_load_projects_invalid_json(self, mocker: MockerFixture) -> None:
        """JSONDecodeError is raised for invalid JSON content."""
        invalid_json = "{ invalid json content"

        mocker.patch("builtins.open", mocker.mock_open(read_data=invalid_json))

        with pytest.raises(json.JSONDecodeError):
            load_projects_from_json("/fake/path/config.json")

    def test_load_projects_permission_error(self, mocker: MockerFixture) -> None:
        """PermissionError is raised when file cannot be read."""
        mocker.patch("builtins.open", side_effect=PermissionError("Permission denied"))

        with pytest.raises(PermissionError):
            load_projects_from_json("/denied/path/config.json")

    def test_load_projects_from_json_success(self, mocker: MockerFixture) -> None:
        """Successful loading of projects from a valid JSON file."""
        sample_json_data: dict[str, dict] = {
            "projects": {
                "project1": {
                    "version": "1.0.0",
                    "config_files": [],
                }
            }
        }

        json_content = json.dumps(sample_json_data)

        mock_root_config = mocker.MagicMock()
        mock_root_config.projects = sample_json_data["projects"]

        mocker.patch("builtins.open", mocker.mock_open(read_data=json_content))
        mocker.patch("json.load", return_value=sample_json_data)
        mock_chdir = mocker.patch("os.chdir")
        mock_from_dict = mocker.patch(
            "vqu.models.RootConfig.from_dict", return_value=mock_root_config
        )

        result = load_projects_from_json("/fake/path/config.json")

        mock_chdir.assert_called_once()
        mock_from_dict.assert_called_once_with(sample_json_data)
        assert result == sample_json_data["projects"]
