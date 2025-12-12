import json

from pydantic import ValidationError
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
        """ValidationError is raised for invalid JSON content."""
        invalid_json = "{ invalid json content"

        # Patching "builtins.open" fails in some environments, so it is replaced by the module
        # scope "vqu.json_config_file.open".
        # See https://github.com/microsoft/vscode-python/issues/24811#issuecomment-3474654627
        mocker.patch("vqu.json_config_file.open", mocker.mock_open(read_data=invalid_json))

        with pytest.raises(ValidationError):
            load_projects_from_json("/fake/path/config.json")

    def test_load_projects_permission_error(self, mocker: MockerFixture) -> None:
        """PermissionError is raised when file cannot be read."""
        mocker.patch("vqu.json_config_file.open", side_effect=PermissionError("Permission denied"))

        with pytest.raises(PermissionError):
            load_projects_from_json("/denied/path/config.json")

    def test_load_projects_from_json_success(self, mocker: MockerFixture) -> None:
        """Successful loading of projects from a valid JSON file."""
        sample_json_data: dict[str, dict] = {
            "projects": {
                "project1": {
                    "version": "1.0.0",
                    "configFiles": [],
                }
            }
        }

        json_content = json.dumps(sample_json_data)
        mocker.patch("vqu.json_config_file.open", mocker.mock_open(read_data=json_content))
        mock_chdir = mocker.patch("os.chdir")

        result = load_projects_from_json("/fake/path/config.json")

        mock_chdir.assert_called_once()

        assert "project1" in result
        json_project1 = sample_json_data["projects"]["project1"]
        assert result["project1"].version == json_project1["version"]
        assert result["project1"].config_files == json_project1["configFiles"]
