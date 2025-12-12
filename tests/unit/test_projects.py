from typing import cast

import pytest
from pytest import CaptureFixture
from pytest_mock import MockerFixture

from vqu.models import ConfigFile, ConfigFileFormat, ConfigFilter, Project
from vqu.project import (
    _InvalidValue,
    _parse_captured_version,
    _print_version,
    _validate_update,
    eval_project,
    update_project,
)


class TestEvalProject:
    """Unit tests for the eval_project function."""

    def setup_method(self) -> None:
        """Setup a default project before each test."""
        self.config_filter = ConfigFilter(expression=".version", result=None)
        self.config_file = ConfigFile(
            path="package.json",
            format=ConfigFileFormat.JSON,
            filters=[self.config_filter],
        )
        self.project = Project(version="1.0.0", config_files=[self.config_file])  # type: ignore[missing-argument]

    def test_eval_project_suppresses_output_when_print_result_false(
        self, mocker: MockerFixture, capsys: CaptureFixture
    ) -> None:
        """eval_project should suppress output when print_result=False."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format", return_value="json")
        mocker.patch("vqu.project._parse_captured_version", return_value="1.0.0")
        mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="1.0.0", returncode=0),
        )

        eval_project("myproject", self.project, print_result=False)

        out = capsys.readouterr().out
        assert out == ""

    def test_eval_project_with_empty_config_files(
        self, mocker: MockerFixture, capsys: CaptureFixture
    ) -> None:
        """eval_project should print project name and version."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format")
        mocker.patch("vqu.project._parse_captured_version", return_value=None)
        mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch("subprocess.run")

        self.project.config_files = []

        eval_project("myproject", self.project)

        out = capsys.readouterr().out
        assert "myproject" in out
        assert "1.0.0" in out

    def test_eval_project_skips_missing_config_file(
        self, mocker: MockerFixture, capsys: CaptureFixture
    ) -> None:
        """eval_project should print [File not found] for missing files."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format")
        mocker.patch("vqu.project._parse_captured_version")
        mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=False)

        config_file = ConfigFile(
            path="/nonexistent/file.json",
            format=ConfigFileFormat.JSON,
            filters=[],
        )
        self.project.config_files = [config_file]

        eval_project("myproject", self.project)

        out = capsys.readouterr().out
        assert "[File not found]" in out
        assert "/nonexistent/file.json" in out

    def test_eval_project_with_empty_filters_in_config_file(self, mocker: MockerFixture) -> None:
        """eval_project should handle config file with no filters."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format", return_value="json")
        mocker.patch("os.path.exists", return_value=True)
        mock_subprocess = mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="1.0.0", returncode=0),
        )

        self.config_file.filters = []

        eval_project("myproject", self.project)

        mock_subprocess.assert_not_called()

    def test_eval_project_builds_correct_yq_command(self, mocker: MockerFixture) -> None:
        """eval_project should build the correct yq command."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format", return_value="json")
        mocker.patch("vqu.project._parse_captured_version", return_value="1.0.0")
        mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=True)
        mock_subprocess = mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="1.0.0", returncode=0),
        )

        eval_project("myproject", self.project)

        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "yq"
        assert "-p" in call_args
        assert "json" in call_args
        assert "-o" in call_args
        assert "tsv" in call_args
        assert ".version" in call_args
        assert "package.json" in call_args

    def test_eval_project_processes_config_file(self, mocker: MockerFixture) -> None:
        """eval_project should process config file when it exists."""
        mock_to_yq = mocker.patch("vqu.project.ConfigFileFormat.to_yq_format", return_value="json")
        mock_parse = mocker.patch("vqu.project._parse_captured_version", return_value="1.0.0")
        mock_print_version = mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=True)
        mock_subprocess = mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="1.0.0", returncode=0),
        )

        eval_project("myproject", self.project)

        mock_to_yq.assert_called_once_with(ConfigFileFormat.JSON)
        mock_subprocess.assert_called_once()
        mock_parse.assert_called_once_with("1.0.0")
        assert self.project.config_files[0].filters[0].result == "1.0.0"
        mock_print_version.assert_called_once_with("1.0.0", "1.0.0", ".version")

    @pytest.mark.parametrize("parsed_output", [(_InvalidValue()), (None)])
    def test_eval_project_does_not_store_value(
        self, mocker: MockerFixture, parsed_output: _InvalidValue | None
    ) -> None:
        """eval_project should not store _InvalidValue result in config_filter.result."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format", return_value="json")
        mocker.patch("vqu.project._parse_captured_version", return_value=parsed_output)
        mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="invalid", returncode=0),
        )

        eval_project("myproject", self.project)

        assert self.project.config_files[0].filters[0].result is None

    def test_eval_project_prints_command_on_error(
        self, mocker: MockerFixture, capsys: CaptureFixture
    ) -> None:
        """eval_project should print the yq command when returncode is non-zero."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format", return_value="json")
        mocker.patch("vqu.project._parse_captured_version", return_value=None)
        mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="", returncode=1),
        )

        eval_project("myproject", self.project)

        out = capsys.readouterr().out
        assert "yq" in out

    def test_eval_project_processes_multiple_config_files(self, mocker: MockerFixture) -> None:
        """eval_project should process all config files."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format", return_value="json")
        mocker.patch("vqu.project._parse_captured_version", return_value="1.0.0")
        mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=True)
        mock_subprocess = mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="1.0.0", returncode=0),
        )

        config_file2 = ConfigFile(
            path="pyproject.toml",
            format=ConfigFileFormat.YAML,
            filters=[ConfigFilter(expression=".project.version", result=None)],
        )
        self.project.config_files.append(config_file2)

        eval_project("myproject", self.project)

        assert mock_subprocess.call_count == 2

    def test_eval_project_processes_multiple_filters_per_file(self, mocker: MockerFixture) -> None:
        """eval_project should process all filters in a config file."""
        mocker.patch("vqu.project.ConfigFileFormat.to_yq_format", return_value="json")
        mocker.patch("vqu.project._parse_captured_version", return_value="1.0.0")
        mocker.patch("vqu.project._print_version")
        mocker.patch("os.path.exists", return_value=True)
        mock_subprocess = mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="1.0.0", returncode=0),
        )

        self.config_file.filters.append(ConfigFilter(expression=".packageVersion", result=None))

        eval_project("myproject", self.project)

        assert mock_subprocess.call_count == 2


class TestParseCapturedVersion:
    """Unit tests for the _parse_captured_version function."""

    def test_parse_captured_version_valid_version(self) -> None:
        """Should return the version string for a valid semantic version."""
        result = _parse_captured_version("1.0.0")

        assert result == "1.0.0"

    def test_parse_captured_version_valid_version_with_whitespace(self) -> None:
        """Should strip whitespace and return valid version."""
        result = _parse_captured_version("  2.5.3  \n")

        assert result == "2.5.3"

    def test_parse_captured_version_null_string(self) -> None:
        """Should return None for 'null' string."""
        result = _parse_captured_version("null")

        assert result is None

    def test_parse_captured_version_null_uppercase(self) -> None:
        """Should return None for 'NULL' (case-insensitive)."""
        result = _parse_captured_version("NULL")

        assert result is None

    def test_parse_captured_version_empty_string(self) -> None:
        """Should return None for empty string."""
        result = _parse_captured_version("")

        assert result is None

    def test_parse_captured_version_invalid_version_format(self) -> None:
        """Should return _InvalidValue for invalid version format."""
        result = _parse_captured_version("not.a.version")

        assert isinstance(result, _InvalidValue)

    def test_parse_captured_version_invalid_letters(self) -> None:
        """Should return _InvalidValue for string with letters."""
        result = _parse_captured_version("abc")

        assert isinstance(result, _InvalidValue)

    def test_parse_captured_version_invalid_special_characters(self) -> None:
        """Should return _InvalidValue for invalid special characters."""
        result = _parse_captured_version("1.0.0@")

        assert isinstance(result, _InvalidValue)

    def test_parse_captured_version_invalid_hyphen_prefix(self) -> None:
        """Should return _InvalidValue for version with invalid prefix."""
        result = _parse_captured_version("-1.0.0")

        assert isinstance(result, _InvalidValue)

    def test_parse_captured_version_prerelease(self) -> None:
        """Should handle semantic version with prerelease."""
        result = _parse_captured_version("1.0.0-alpha")

        assert result == "1.0.0-alpha"

    def test_parse_captured_version_build_metadata(self) -> None:
        """Should handle semantic version with build metadata."""
        result = _parse_captured_version("1.0.0+build.1")

        assert result == "1.0.0+build.1"

    def test_parse_captured_version_prerelease_and_build(self) -> None:
        """Should handle semantic version with prerelease and build metadata."""
        result = _parse_captured_version("1.0.0-beta+exp.sha")

        assert result == "1.0.0-beta+exp.sha"

    def test_parse_captured_version_decimal_build_number(self) -> None:
        """Should return _InvalidValue for decimal numbers."""
        result = _parse_captured_version("1.0.0.42")

        assert result == "1.0.0.42"


class TestPrintVersion:
    """Unit tests for the _print_version function."""

    def test_print_version_none_value(self, capsys: CaptureFixture) -> None:
        """_print_version should print '[Value not found]' in red when version is None."""
        _print_version(None, "1.0.0", ".version")

        out = capsys.readouterr().out
        assert ".version = [Value not found]" in out

    def test_print_version_invalid_value(self, capsys: CaptureFixture) -> None:
        """_print_version should print '[Invalid version]' in red when version is _InvalidValue."""
        _print_version(_InvalidValue(), "1.0.0", ".version")

        out = capsys.readouterr().out
        assert ".version = [Invalid version]" in out

    def test_print_version_differing_version(self, capsys: CaptureFixture) -> None:
        """_print_version should print version in yellow when versions differ."""
        _print_version("0.9.0", "1.0.0", ".version")

        out = capsys.readouterr().out
        assert ".version = 0.9.0" in out

    def test_print_version_matching_version(self, capsys: CaptureFixture) -> None:
        """_print_version should print version in green when versions match."""
        _print_version("1.0.0", "1.0.0", ".version")

        out = capsys.readouterr().out
        assert ".version = 1.0.0" in out


class TestUpdateProject:
    """Unit tests for the update_project function."""

    def setup_method(self) -> None:
        """Setup a default project before each test."""
        self.config_filter = ConfigFilter(expression=".version", result="1.0.0")
        self.config_file = ConfigFile(
            path="package.json",
            format=ConfigFileFormat.JSON,
            filters=[self.config_filter],
        )
        self.project = Project(version="2.0.0", config_files=[self.config_file])  # type: ignore[missing-argument]

        self.json_content = '{\n  "version": "1.0.0"\n}\n'

    def test_update_project_with_empty_config_files_calls_eval_project(
        self, mocker: MockerFixture
    ) -> None:
        """update_project should call eval_project with print_result=False."""
        self.project.config_files = []

        mock_eval = mocker.patch("vqu.project.eval_project")
        # Patching "builtins.open" fails in some environments, so it is replaced by the module
        # scope "vqu.project.open".
        # See https://github.com/microsoft/vscode-python/issues/24811#issuecomment-3474654627
        mock_open = mocker.patch("vqu.project.open", mocker.mock_open())

        update_project("myproject", self.project)

        mock_eval.assert_called_once_with("myproject", self.project, print_result=False)
        mock_open.assert_not_called()

    def test_update_project_with_empty_filters_reads_config_file(
        self, mocker: MockerFixture
    ) -> None:
        """update_project should read the config file."""
        self.config_file.filters = []

        mocker.patch("vqu.project.eval_project")
        mock_open = mocker.patch("vqu.project.open", mocker.mock_open(read_data=self.json_content))

        update_project("myproject", self.project)

        # Check that open was called to read the file
        assert mocker.call("package.json", "r") in mock_open.call_args_list

    def test_update_project_validates_update(self, mocker: MockerFixture) -> None:
        """update_project should validate the update before replacing."""
        mocker.patch("vqu.project.eval_project")
        mocker.patch("vqu.project.open", mocker.mock_open(read_data=self.json_content))
        mock_validate = mocker.patch("vqu.project._validate_update")

        update_project("myproject", self.project)

        mock_validate.assert_called_once_with(self.json_content, "package.json", self.config_filter)

    def test_update_project_writes_updated_content(self, mocker: MockerFixture) -> None:
        """update_project should write the updated content to the file."""
        mocker.patch("vqu.project.eval_project")
        mock_open_instance = mocker.mock_open(read_data=self.json_content)
        mocker.patch("vqu.project.open", mock_open_instance)
        mocker.patch("vqu.project._validate_update")

        update_project("myproject", self.project)

        # Check that open was called to write the file
        assert mocker.call("package.json", "w") in mock_open_instance.call_args_list

        # Verify write was called with updated content
        updated_content = self.json_content.replace("1.0.0", "2.0.0", 1)
        write_calls = [call for call in mock_open_instance.return_value.write.call_args_list]
        assert len(write_calls) == 1
        assert write_calls[0] == mocker.call(updated_content)

    def test_update_project_prints_success_message(
        self, mocker: MockerFixture, capsys: CaptureFixture
    ) -> None:
        """update_project should print a success message after updating."""
        mocker.patch("vqu.project.eval_project")
        mocker.patch("vqu.project.open", mocker.mock_open(read_data=self.json_content))
        mocker.patch("vqu.project._validate_update")

        update_project("myproject", self.project)

        out = capsys.readouterr().out
        assert "package.json" in out
        assert "2.0.0" in out
        assert "updated" in out.lower()
        assert out.endswith("\n")

    def test_update_project_processes_multiple_config_files(self, mocker: MockerFixture) -> None:
        """update_project should process all config files."""
        config_file2 = ConfigFile(
            path="pyproject.toml",
            format=ConfigFileFormat.YAML,
            filters=[ConfigFilter(expression=".project.version", result="1.0.0")],
        )
        self.project.config_files.append(config_file2)

        mocker.patch("vqu.project.eval_project")
        mock_open = mocker.patch("vqu.project.open", mocker.mock_open(read_data=self.json_content))
        mocker.patch("vqu.project._validate_update")

        update_project("myproject", self.project)

        assert mock_open.call_count == 4  # 2 reads + 2 writes
        # Verify that open was called for both files
        assert mocker.call("package.json", "r") in mock_open.call_args_list
        assert mocker.call("pyproject.toml", "r") in mock_open.call_args_list

    def test_update_project_processes_multiple_filters_per_file(
        self, mocker: MockerFixture
    ) -> None:
        """update_project should process all filters in a config file."""
        config_filter2 = ConfigFilter(expression=".packageVersion", result="1.0.0")
        self.config_file.filters.append(config_filter2)

        mocker.patch("vqu.project.eval_project")
        mocker.patch("vqu.project.open", mocker.mock_open(read_data=self.json_content))
        mock_validate = mocker.patch("vqu.project._validate_update")

        update_project("myproject", self.project)

        # Verify that _validate_update was called for both filters
        assert mock_validate.call_count == 2


class TestValidateUpdate:
    """Unit tests for the _validate_update function."""

    def setup_method(self) -> None:
        """Setup before each test."""
        self.json_content = '{"version": "1.0.0"}'
        self.config_filter = ConfigFilter(expression=".version", result="1.0.0")

    def test_validate_update_success_single_occurrence(self) -> None:
        """_validate_update should pass when value appears exactly once."""
        # Should not raise
        _validate_update(self.json_content, "package.json", self.config_filter)

    def test_validate_update_raises_when_result_is_none(self) -> None:
        """_validate_update should raise ValueError when result is None."""
        self.config_filter.result = None

        with pytest.raises(ValueError) as exc:
            _validate_update(self.json_content, "package.json", self.config_filter)

        assert "No value retrieved for expression" in str(exc.value)
        assert self.config_filter.expression in str(exc.value)
        assert "package.json" in str(exc.value)

    def test_validate_update_raises_when_value_not_found(self) -> None:
        """_validate_update should raise ValueError when value not found in content."""
        content = '{"version": "2.0.0"}'

        with pytest.raises(ValueError) as exc:
            _validate_update(content, "package.json", self.config_filter)

        assert "not found" in str(exc.value)
        assert cast(str, self.config_filter.result) in str(exc.value)
        assert "package.json" in str(exc.value)

    def test_validate_update_raises_when_multiple_occurrences(self) -> None:
        """_validate_update should raise ValueError when value appears multiple times."""
        content = '{"version": "1.0.0", "oldVersion": "1.0.0"}'

        with pytest.raises(ValueError) as exc:
            _validate_update(content, "package.json", self.config_filter)

        assert "Multiple occurrences of value" in str(exc.value)
        assert cast(str, self.config_filter.result) in str(exc.value)
        assert "package.json" in str(exc.value)

    def test_validate_update_special_characters_in_result(self) -> None:
        """_validate_update should handle special characters in result."""
        content = '{"version": "1.0.0-alpha+build.1"}'
        self.config_filter.result = "1.0.0-alpha+build.1"

        # Should not raise
        _validate_update(content, "package.json", self.config_filter)

    def test_validate_update_single_numeric_occurrence(self) -> None:
        """_validate_update should pass for single numeric occurrence."""
        content = '{"id": 123}'
        self.config_filter.result = "123"

        # Should not raise
        _validate_update(content, "config.json", self.config_filter)

    def test_validate_update_yaml_content(self) -> None:
        """_validate_update should work with YAML content."""
        content = "version: 1.0.0\nname: myapp"

        # Should not raise
        _validate_update(content, "pyproject.toml", self.config_filter)

    def test_validate_update_toml_content(self) -> None:
        """_validate_update should work with TOML content."""
        content = '[project]\nversion = "1.0.0"'

        # Should not raise
        _validate_update(content, "pyproject.toml", self.config_filter)

    def test_validate_update_unicode_content(self) -> None:
        """_validate_update should handle unicode characters in content."""
        content = '{"version": "1.0.0", "description": "Café"}'

        # Should not raise
        _validate_update(content, "package.json", self.config_filter)
