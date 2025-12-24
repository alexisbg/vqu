from pydantic import ValidationError
import pytest

from vqu.models import CliArgs, ConfigFile, ConfigFileFormat, ConfigFilter, Project, RootConfig


class TestCliArgs:
    """Unit tests for the CliArgs class."""

    @pytest.mark.parametrize(
        "proj,path,update",
        [
            (42, "/path/.vqu.yaml", True),
            ("project1", 42, True),
            (None, "/path/.vqu.yaml", "wrong_type"),
        ],
    )
    def test_cli_args_invalid_type(self, proj: str | None, path: str, update: bool) -> None:
        """ValidationError is raised for invalid types."""
        with pytest.raises(ValidationError):
            CliArgs(project=proj, config_file_path=path, update=update)

    def test_cli_args_valid_creation(self) -> None:
        """Successful creation of CliArgs with valid data."""
        sut = CliArgs(project="project1", config_file_path="/path/.vqu.yaml", update=True)

        assert isinstance(sut.project, str)
        assert sut.config_file_path == "/path/.vqu.yaml"
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


class TestConfigFilter:
    """Unit tests for the ConfigFilter class."""

    @pytest.mark.parametrize("expression", [42, ""])
    def test_config_filter_invalid_expression_type(self, expression: str) -> None:
        """ValidationError is raised for invalid expression types."""
        with pytest.raises(ValidationError):
            ConfigFilter(expression=expression)

    def test_config_filter_invalid_validate_docker_tag_type(self) -> None:
        """ValidationError is raised for invalid validate_docker_tag types."""
        with pytest.raises(ValidationError):
            ConfigFilter(expression=".version", validate_docker_tag="not_bool")  # type: ignore[invalid-argument-type]

    def test_config_filter_invalid_validate_regex_type(self) -> None:
        """ValidationError is raised for invalid validate_regex types."""
        with pytest.raises(ValidationError):
            ConfigFilter(expression=".version", validate_regex=42)  # type: ignore[bad-argument-type]

    def test_config_filter_invalid_result_type(self) -> None:
        """ValidationError is raised for invalid result types."""
        with pytest.raises(ValidationError):
            sut = ConfigFilter(expression=".version")
            sut.result = 42  # type: ignore[bad-assignment]

    def test_config_filter_keep_result_none(self) -> None:
        """Result set to None remains None."""
        sut = ConfigFilter(expression=".version")
        sut.result = None

        assert sut.result is None

    def test_config_filter_strip_result_whitespace(self) -> None:
        """Result with leading/trailing whitespace is stripped."""
        sut = ConfigFilter(expression=".version")
        sut.result = "  1.0  \n"

        assert sut.result == "1.0"

    @pytest.mark.parametrize("result", [(""), ("   "), ("null"), ("NULL")])
    def test_config_filter_result_set_to_empty_string_or_null_string(self, result: str) -> None:
        """Result set to empty string or null string becomes None."""
        sut = ConfigFilter(expression=".version")
        sut.result = result

        assert sut.result is None

    def test_config_filter_invalid_result_with_expression_only(self) -> None:
        """ValidationError raised for invalid result."""
        with pytest.raises(ValidationError):
            sut = ConfigFilter(expression=".version")
            sut.result = "1.0.0-invalid"

    def test_config_filter_invalid_result_with_validate_docker_tag(self) -> None:
        """ValidationError raised for invalid Docker tag result."""
        with pytest.raises(ValidationError):
            sut = ConfigFilter(expression=".version", validate_docker_tag=True)
            sut.result = "invalid.tag!"

    def test_config_filter_invalid_result_with_validate_regex(self) -> None:
        """ValidationError raised for result not matching regex pattern."""
        with pytest.raises(ValidationError):
            sut = ConfigFilter(expression=".version", validate_regex=r"^v\d+\.\d+\.\d+$")
            sut.result = "1.2.3"

    def test_config_filter_invalid_result_with_special_characters(self) -> None:
        """ValidationError raised for result with special characters."""
        with pytest.raises(ValidationError):
            sut = ConfigFilter(expression=".version")
            sut.result = "1.0.0@"

    def test_config_filter_invalid_result_with_hyphen_prefix(self) -> None:
        """ValidationError raised for result with hyphen prefix."""
        with pytest.raises(ValidationError):
            sut = ConfigFilter(expression=".version")
            sut.result = "-1.0.0"

    def test_config_filter_valid_result_with_expression_only(self) -> None:
        """Result setter validates with expression only."""
        sut = ConfigFilter(expression=".version")
        sut.result = "2.0.0"

        assert sut.expression == ".version"
        assert sut.result == "2.0.0"

    def test_config_filter_valid_result_with_validate_docker_tag(self) -> None:
        """Result setter validates with valid Docker tag."""
        sut = ConfigFilter(expression=".version", validate_docker_tag=True)
        sut.result = "1.0-alpha_1"

        assert sut.validate_docker_tag is True
        assert sut.result == "1.0-alpha_1"

    def test_config_filter_valid_result_with_validate_regex(self) -> None:
        """Result setter validates with result matching regex pattern."""
        sut = ConfigFilter(expression=".version", validate_regex=r"^v\d+\.\d+\.\d+$")
        sut.result = "v1.2.3"

        assert sut.validate_regex == r"^v\d+\.\d+\.\d+$"
        assert sut.result == "v1.2.3"

    def test_config_filter_valid_result_with_v_prefix(self) -> None:
        """Result setter validates with 'v' prefix in version."""
        sut = ConfigFilter(expression=".app.version")
        sut.result = "v1.0.0"

        assert sut.result == "v1.0.0"

    def test_config_filter_valid_result_with_prerelease(self) -> None:
        """Result setter validates with prerelease version."""
        sut = ConfigFilter(expression=".app.version")
        sut.result = "1.0.0-beta.1"

        assert sut.result == "1.0.0-beta.1"

    def test_config_filter_valid_result_with_build_metadata(self) -> None:
        """Result setter validates with build metadata in version."""
        sut = ConfigFilter(expression=".app.version")
        sut.result = "1.0.0+build.123"

        assert sut.result == "1.0.0+build.123"

    def test_config_filter_valid_result_with_prerelease_and_build_metadata(self) -> None:
        """Result setter validates with prerelease and build metadata."""
        sut = ConfigFilter(expression=".app.version")
        sut.result = "1.0.0-rc.1+build.456"

        assert sut.result == "1.0.0-rc.1+build.456"

    def test_config_filter_valid_result_with_decimal_build_number(self) -> None:
        """Result setter validates with decimal build number."""
        sut = ConfigFilter(expression=".app.version")
        sut.result = "2.1.0.42"

        assert sut.result == "2.1.0.42"

    def test_config_filter_valid_creation_with_result(self) -> None:
        """Successful creation of ConfigFilter instance with result."""
        sut = ConfigFilter(expression=".app.version", result="1.2.3")

        assert sut.expression == ".app.version"
        assert sut.result == "1.2.3"

    def test_config_filter_docker_tag_precedence_over_regex(self) -> None:
        """Docker tag validation takes precedence over regex validation."""
        sut = ConfigFilter(
            expression=".version",
            validate_docker_tag=True,
            validate_regex=r"^v\d+\.\d+\.\d+$",
        )
        sut.result = "2.4.2-beta"

        assert sut.result == "2.4.2-beta"


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
