from pydantic import ValidationError
import pytest
from pytest_mock import MockerFixture

from vqu.models import CliArgs, ConfigFile, ConfigFileFormat, ConfigFilter, Project, RootConfig


class TestCliArgs:
    """Unit tests for the CliArgs class."""

    @pytest.mark.parametrize(
        "proj,path,update",
        [
            (42, "/path/.vqu.json", True),
            ("project1", 42, True),
            (None, "/path/.vqu.json", "wrong_type"),
        ],
    )
    def test_cli_args_invalid_type(self, proj: str | None, path: str, update: bool) -> None:
        """ValidationError is raised for invalid types."""
        with pytest.raises(ValidationError):
            CliArgs(project=proj, config_file_path=path, update=update)

    def test_cli_args_valid_creation(self) -> None:
        """Successful creation of CliArgs with valid data."""
        sut = CliArgs(project="project1", config_file_path="/path/.vqu.json", update=True)

        assert isinstance(sut.project, str)
        assert sut.config_file_path == "/path/.vqu.json"
        assert sut.update is True


class TestRootConfig:
    """Unit tests for the RootConfig class."""

    invalid_projects = [
        {"project1": "not_a_dict"},  # projects not a dict
        {42: {}},  # projects as list instead of dict
    ]

    @pytest.mark.parametrize("projects", invalid_projects)
    def test_root_config_invalid_type(self, projects: dict[str, Project]) -> None:
        """Test ValidationError is raised for invalid types."""
        with pytest.raises(ValidationError):
            RootConfig(projects=projects)

    def test_root_config_valid_creation(self) -> None:
        """Successful creation of RootConfig with valid data."""
        data = {"proj1": Project(version="1.0", config_files=[])}

        sut = RootConfig(projects=data)

        assert isinstance(sut.projects, dict)
        assert len(sut.projects) == 1
        assert "proj1" in sut.projects
        assert isinstance(sut.projects["proj1"], Project)

    @pytest.mark.parametrize("projects", invalid_projects)
    def test_from_dict_invalid_projects_type(self, projects: dict[str, Project]) -> None:
        """ValidationError when 'projects' is of invalid type."""
        with pytest.raises((KeyError, TypeError)):  # pyrefly: ignore[no-matching-overload]
            RootConfig.from_dict({"projects": projects})

    def test_from_dict_empty_projects(self, mocker: MockerFixture) -> None:
        """Successful creation with empty projects dict."""
        data = {"projects": {}}

        root = RootConfig.from_dict(data)

        assert isinstance(root.projects, dict)
        assert root.projects == {}

    def test_from_dict_valid(self, mocker: MockerFixture) -> None:
        """Successful creation of RootConfig from a valid dictionary."""
        data = {
            "projects": {
                "proj1": {"version": "1.0", "config_files": []},
                "proj2": {"version": "2.0", "config_files": []},
            }
        }

        root = RootConfig.from_dict(data)

        assert isinstance(root.projects, dict)
        assert len(root.projects) == 2
        assert "proj1" in root.projects
        assert "proj2" in root.projects


class TestProject:
    """Unit tests for the Project class."""

    invalid_version = [
        (42),  # version not a string
        (""),  # version empty string
    ]
    invalid_config_files = [
        ("not_a_list"),  # config_files not a list
        ([42]),  # config_files contains non-dict
    ]

    @pytest.mark.parametrize("version", invalid_version)
    def test_project_invalid_version_type(self, version: str) -> None:
        """ValidationError is raised for invalid version types."""
        with pytest.raises(ValidationError):
            Project(version=version, config_files=[])

    @pytest.mark.parametrize("config_files", invalid_config_files)
    def test_project_invalid_config_files_type(self, config_files: list) -> None:
        """ValidationError is raised for invalid config_files types."""
        with pytest.raises(ValidationError):
            Project(version="1.0", config_files=config_files)

    def test_project_valid_creation(self) -> None:
        """Successful creation of Project with valid data."""
        sut = Project(version="1.0", config_files=[])

        assert isinstance(sut.version, str)
        assert sut.version == "1.0"
        assert isinstance(sut.config_files, list)
        assert len(sut.config_files) == 0

    @pytest.mark.parametrize("version", invalid_version)
    def test_from_dict_invalid_version_type(self, version: str) -> None:
        """ValidationError for invalid version types."""
        with pytest.raises(ValidationError):
            Project.from_dict({"version": version, "config_files": []})

    @pytest.mark.parametrize("config_files", invalid_config_files)
    def test_from_dict_invalid_config_files_type(self, config_files: list) -> None:
        """TypeError for invalid config_files type."""
        with pytest.raises(TypeError):
            Project.from_dict({"version": "1.0", "config_files": config_files})

    def test_from_dict_empty_config_files(self) -> None:
        """from_dict successful with empty config_files list."""
        data = {"version": "1.0", "config_files": []}

        project = Project.from_dict(data)

        assert isinstance(project, Project)
        assert project.version == "1.0"
        assert project.config_files == []

    def test_from_dict_valid(self) -> None:
        """from_dict successful with a valid config_files."""
        data = {
            "version": "2.5.0",
            "config_files": [
                {
                    "path": "config.json",
                    "format": "json",
                    "filters": [{"expression": ".version", "result": None}],
                }
            ],
        }

        project = Project.from_dict(data)

        assert isinstance(project, Project)
        assert project.version == "2.5.0"
        assert len(project.config_files) == 1
        assert project.config_files[0].path == "config.json"


class TestConfigFile:
    """Unit tests for the ConfigFile class."""

    invalid_path = [
        (42),  # path not a string
        (""),  # path empty string
    ]
    invalid_format = [
        (42),  # format not a string
        ("invalid_format"),  # format not a valid ConfigFileFormat
    ]
    invalid_filters = [
        ("not_a_list"),  # filters not a list
        ([42]),  # filters contains non-dict
    ]

    @pytest.mark.parametrize("path", invalid_path)
    def test_config_file_invalid_path_type(self, path: str) -> None:
        """ValidationError is raised for invalid path types."""
        with pytest.raises(ValidationError):
            ConfigFile(path=path, format=ConfigFileFormat.JSON, filters=[])

    @pytest.mark.parametrize("format", invalid_format)
    def test_config_file_invalid_format_type(self, format: ConfigFileFormat) -> None:
        """ValidationError is raised for invalid format types."""
        with pytest.raises(ValidationError):
            ConfigFile(path="config.json", format=format, filters=[])

    @pytest.mark.parametrize("filters", invalid_filters)
    def test_config_file_invalid_filters_type(self, filters: list) -> None:
        """ValidationError is raised for invalid filters type."""
        with pytest.raises(ValidationError):
            ConfigFile(path="config.json", format=ConfigFileFormat.JSON, filters=filters)

    def test_config_file_valid_creation(self) -> None:
        """Successful creation of ConfigFile with valid data."""
        sut = ConfigFile(path="config.json", format=ConfigFileFormat.JSON, filters=[])

        assert isinstance(sut.path, str)
        assert sut.path == "config.json"
        assert sut.format == ConfigFileFormat.JSON
        assert isinstance(sut.filters, list)
        assert len(sut.filters) == 0

    @pytest.mark.parametrize("path", invalid_path)
    def test_from_dict_invalid_path_type(self, path: str) -> None:
        """ValidationError for invalid path types."""
        with pytest.raises(ValidationError):
            ConfigFile.from_dict({"path": path, "format": ConfigFileFormat.JSON, "filters": []})

    @pytest.mark.parametrize("format", invalid_path)
    def test_from_dict_invalid_format_type(self, format: ConfigFileFormat) -> None:
        """ValueError for invalid format types."""
        with pytest.raises(ValueError):
            ConfigFile.from_dict({"path": "config.json", "format": format, "filters": []})

    @pytest.mark.parametrize("filters", invalid_filters)
    def test_from_dict_invalid_filters_type(self, filters: list) -> None:
        """TypeError for invalid filters type."""
        with pytest.raises(TypeError):
            ConfigFile.from_dict(
                {"path": "config.json", "format": ConfigFileFormat.JSON, "filters": filters}
            )

    def test_from_dict_empty_filters(self) -> None:
        """Successful creation with empty filters list."""
        data = {"path": "config.json", "format": "json", "filters": []}

        config_file = ConfigFile.from_dict(data)

        assert isinstance(config_file, ConfigFile)
        assert config_file.path == "config.json"
        assert config_file.format == ConfigFileFormat.JSON
        assert config_file.filters == []

    def test_from_dict_valid(self) -> None:
        """Successful creation of ConfigFile from a valid dictionary."""
        data = {
            "path": "config.yaml",
            "format": "yaml",
            "filters": [
                {"expression": ".version", "result": None},
                {"expression": ".app.version", "result": "1.2.3"},
            ],
        }

        config_file = ConfigFile.from_dict(data)

        assert isinstance(config_file, ConfigFile)
        assert config_file.path == "config.yaml"
        assert config_file.format == ConfigFileFormat.YAML
        assert len(config_file.filters) == 2
        assert config_file.filters[0].expression == ".version"
        assert config_file.filters[1].result == "1.2.3"


class TestConfigFilter:
    """Unit tests for the ConfigFilter class."""

    invalid_expression = [
        (42),  # expression not a string
        (""),  # empty string
    ]
    invalid_result = [
        (42),  # result not a string or None
    ]

    @pytest.mark.parametrize("expression", invalid_expression)
    def test_config_filter_invalid_expression_type(self, expression: str) -> None:
        """ValidationError is raised for invalid expression types."""
        with pytest.raises(ValidationError):
            ConfigFilter(expression=expression, result=None)

    @pytest.mark.parametrize("result", invalid_result)
    def test_config_filter_invalid_result_type(self, result: str | None) -> None:
        """ValidationError is raised for invalid result types."""
        with pytest.raises(ValidationError):
            ConfigFilter(expression=".version", result=result)

    def test_config_filter_valid_creation_without_result(self) -> None:
        """Successful creation of ConfigFilter without result."""
        sut = ConfigFilter(expression=".version")

        assert isinstance(sut.expression, str)
        assert sut.expression == ".version"
        assert sut.result is None

    def test_config_filter_valid_creation_with_result(self) -> None:
        """Successful creation of ConfigFilter with result."""
        sut = ConfigFilter(expression=".app.version", result="1.2.3")

        assert isinstance(sut.expression, str)
        assert sut.expression == ".app.version"
        assert isinstance(sut.result, str)
        assert sut.result == "1.2.3"

    @pytest.mark.parametrize("expression", invalid_expression)
    def test_from_dict_invalid_expression_type(self, expression: str) -> None:
        """ValidationError for invalid expression types."""
        with pytest.raises(ValidationError):
            ConfigFilter.from_dict({"expression": expression, "result": None})

    @pytest.mark.parametrize("result", invalid_result)
    def test_from_dict_invalid_result_type(self, result: str | None) -> None:
        """ValidationError for invalid result types."""
        with pytest.raises(ValidationError):
            ConfigFilter.from_dict({"expression": ".version", "result": result})

    def test_from_dict_valid_without_result(self) -> None:
        """Successful creation of ConfigFilter from a valid dictionary without result."""
        data = {"expression": ".database.version"}

        config_filter = ConfigFilter.from_dict(data)

        assert isinstance(config_filter, ConfigFilter)
        assert config_filter.expression == ".database.version"
        assert config_filter.result is None

    def test_from_dict_valid_with_result(self) -> None:
        """Successful creation of ConfigFilter from a valid dictionary with result."""
        data = {"expression": ".app.version", "result": "2.3.4"}

        config_filter = ConfigFilter.from_dict(data)

        assert isinstance(config_filter, ConfigFilter)
        assert config_filter.expression == ".app.version"
        assert config_filter.result == "2.3.4"


class TestConfigFileFormat:
    """Unit tests for the ConfigFileFormat enum."""

    def test_enum_values(self) -> None:
        """The enum has the expected values."""
        assert ConfigFileFormat.DOTENV == "dotenv"
        assert ConfigFileFormat.JSON == "json"
        assert ConfigFileFormat.TOML == "toml"
        assert ConfigFileFormat.XML == "xml"
        assert ConfigFileFormat.YAML == "yaml"

    def test_has_value_valid(self) -> None:
        """Has_value returns True for valid enum values."""
        assert ConfigFileFormat.has_value("dotenv") is True
        assert ConfigFileFormat.has_value("json") is True
        assert ConfigFileFormat.has_value("toml") is True
        assert ConfigFileFormat.has_value("xml") is True
        assert ConfigFileFormat.has_value("yaml") is True

    def test_has_value_invalid(self) -> None:
        """Has_value returns False for invalid values."""
        assert ConfigFileFormat.has_value("invalid") is False
        assert ConfigFileFormat.has_value("") is False
        assert ConfigFileFormat.has_value("JSON") is False  # case sensitive
        assert ConfigFileFormat.has_value(" json ") is False  # no whitespace

    def test_to_yq_format_dotenv(self) -> None:
        """To_yq_format converts DOTENV to 'props'."""
        result = ConfigFileFormat.to_yq_format(ConfigFileFormat.DOTENV)
        assert result == "props"
