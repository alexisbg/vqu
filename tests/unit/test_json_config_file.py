from pydantic import ValidationError
import pytest
from pytest_mock import MockerFixture
import yaml
from yaml.parser import ParserError

from vqu.yaml_file import load_projects_from_yaml


class TestLoadProjectsFromYaml:
    """Unit tests for the load_projects_from_yaml function."""

    def test_load_projects_from_yaml_not_found(self) -> None:
        """FileNotFoundError is raised when the file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_projects_from_yaml("/nonexistent/path/.vqu.yaml")

    def test_load_projects_invalid_yaml(self, mocker: MockerFixture) -> None:
        """ValidationError is raised for invalid YAML content."""
        invalid_yaml = "{ invalid yaml content"

        # Patching "builtins.open" fails in some environments, so it is replaced by the module
        # scope "vqu.yaml_file.open".
        # See https://github.com/microsoft/vscode-python/issues/24811#issuecomment-3474654627
        mocker.patch("vqu.yaml_file.open", mocker.mock_open(read_data=invalid_yaml))

        with pytest.raises(ParserError):
            load_projects_from_yaml("/fake/path/config.yaml")

    def test_load_projects_invalid_yaml_structure(self, mocker: MockerFixture) -> None:
        """ValidationError is raised for YAML content with invalid structure."""
        yaml_data: dict[str, dict] = {
            "projects": {
                "project1": {
                    "invalidField": 42,
                }
            }
        }
        yaml_content = yaml.dump(yaml_data, default_flow_style=False)

        mocker.patch("vqu.yaml_file.open", mocker.mock_open(read_data=yaml_content))

        with pytest.raises(ValidationError):
            load_projects_from_yaml("/fake/path/config.yaml")

    def test_load_projects_permission_error(self, mocker: MockerFixture) -> None:
        """PermissionError is raised when file cannot be read."""
        mocker.patch("vqu.yaml_file.open", side_effect=PermissionError("Permission denied"))

        with pytest.raises(PermissionError):
            load_projects_from_yaml("/denied/path/config.yaml")

    def test_load_projects_from_yaml_success(self, mocker: MockerFixture) -> None:
        """Successful loading of projects from a valid YAML file."""
        yaml_data: dict[str, dict] = {
            "projects": {
                "project1": {
                    "version": "1.0.0",
                    "configFiles": [],
                }
            }
        }
        yaml_content = yaml.dump(yaml_data, default_flow_style=False)

        mocker.patch("vqu.yaml_file.open", mocker.mock_open(read_data=yaml_content))
        mock_chdir = mocker.patch("os.chdir")

        result = load_projects_from_yaml("/fake/path/config.yaml")

        mock_chdir.assert_called_once()

        assert "project1" in result
        yaml_project1 = yaml_data["projects"]["project1"]
        assert result["project1"].version == yaml_project1["version"]
        assert result["project1"].config_files == yaml_project1["configFiles"]
