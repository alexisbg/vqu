import pytest
from pytest import CaptureFixture
from pytest_mock import MockerFixture

from vqu import cli
from vqu.models import CliArgs, Project


class TestMain:
    """Unit tests for the main function."""

    def test_exit_when_exception(self, mocker: MockerFixture, capsys: CaptureFixture) -> None:
        """Main should print an error and exit with code 1 when an exception is raised."""
        mocker.patch.object(cli, "check_yq")  # Assume yq is present
        mocker.patch.object(cli, "get_cli_args")  # Assume args are fine
        mocker.patch.object(cli, "load_projects_from_yaml")  # Assume loading works
        mocker.patch.object(cli, "handle_args", side_effect=Exception("Unexpected error"))

        with pytest.raises(SystemExit) as se:
            cli.main()

        out: str = capsys.readouterr().out
        bold = "\x1b[1m"
        red = "\x1b[31m"
        reset = "\x1b[0m"
        assert out.startswith(f"{bold}{red}[Error]{reset} Unexpected error")
        assert se.value.code == 1


class TestCheckYq:
    """Unit tests for the check_yq function."""

    def test_raise_file_not_found_when_yq_missing(self, mocker: MockerFixture) -> None:
        """check_yq should raise FileNotFoundError when 'yq' is not found."""
        mocker.patch("shutil.which", return_value=None)

        with pytest.raises(FileNotFoundError) as exc:
            cli.check_yq()

        assert "'yq' command not found" in str(exc.value)
        assert "Please install 'yq' to proceed" in str(exc.value)

    def test_success_when_yq_exists(self, mocker: MockerFixture) -> None:
        """check_yq should not raise when 'yq' is found in PATH."""
        mock_which = mocker.patch("shutil.which", return_value="/usr/bin/yq")

        cli.check_yq()  # Should not raise

        mock_which.assert_called_once_with("yq")


class TestGetCliArgs:
    """Unit tests for the get_cli_args function."""

    def test_no_arguments(self, mocker: MockerFixture) -> None:
        """get_cli_args with no arguments should return defaults."""
        mocker.patch("sys.argv", ["vqu"])

        args = cli.get_cli_args()

        assert isinstance(args, CliArgs)
        assert args.project is None
        assert args.config_file_path == ".vqu.yaml"
        assert args.update is False

    def test_with_project(self, mocker: MockerFixture) -> None:
        """get_cli_args with project name should set project attribute."""
        mocker.patch("sys.argv", ["vqu", "myproject"])

        args = cli.get_cli_args()

        assert args.project == "myproject"
        assert args.config_file_path == ".vqu.yaml"
        assert args.update is False

    def test_with_config_long_option(self, mocker: MockerFixture) -> None:
        """get_cli_args with --config option should set config_file_path."""
        mocker.patch("sys.argv", ["vqu", "--config", "/custom/.vqu.yaml"])

        args = cli.get_cli_args()

        assert args.project is None
        assert args.config_file_path == "/custom/.vqu.yaml"
        assert args.update is False

    def test_with_update_flag(self, mocker: MockerFixture) -> None:
        """get_cli_args with --update flag should set update to True."""
        mocker.patch("sys.argv", ["vqu", "myproject", "-u"])

        args = cli.get_cli_args()

        assert args.project == "myproject"
        assert args.config_file_path == ".vqu.yaml"
        assert args.update is True


class TestHandleArgs:
    """Unit tests for the handle_args function."""

    def setup_method(self) -> None:
        """Setup before each test."""
        self.project1 = Project(version="1.0.0", config_files=[])
        self.project2 = Project(version="2.0.0", config_files=[])
        self.projects = {"project1": self.project1, "project2": self.project2}

    def test_raise_value_error_when_update_without_project(self) -> None:
        """handle_args should raise ValueError when --update is used without a project."""
        args = CliArgs(project=None, config_file_path=".vqu.yaml", update=True)

        with pytest.raises(ValueError) as exc:
            cli.handle_args(args, self.projects)

        assert "The --update option requires a specific project to be specified" in str(exc.value)

    def test_raise_value_error_when_project_not_found(self) -> None:
        """handle_args should raise ValueError when specified project not found."""
        args = CliArgs(project="nonexistent", config_file_path=".vqu.yaml", update=False)

        with pytest.raises(ValueError) as exc:
            cli.handle_args(args, self.projects)

        assert "Project 'nonexistent' not found in configuration" in str(exc.value)

    def test_call_eval_project_when_project_specified(self, mocker: MockerFixture) -> None:
        """handle_args should call eval_project when a project is specified."""
        mock_eval = mocker.patch.object(cli, "eval_project")
        mock_update = mocker.patch.object(cli, "update_project")

        args = CliArgs(project="project2", config_file_path=".vqu.yaml", update=False)

        cli.handle_args(args, self.projects)

        assert mocker.call("project1", self.project1) not in mock_eval.call_args_list
        assert mocker.call("project2", self.project2) in mock_eval.call_args_list
        mock_update.assert_not_called()

    def test_call_both_update_and_eval_when_update_flag_set(self, mocker: MockerFixture) -> None:
        """handle_args should call both update_project and eval_project with --update."""
        mock_update = mocker.patch.object(cli, "update_project")
        mock_eval = mocker.patch.object(cli, "eval_project")

        args = CliArgs(project="project2", config_file_path=".vqu.yaml", update=True)

        cli.handle_args(args, self.projects)

        mock_update.assert_called_once_with("project2", self.project2)
        mock_eval.assert_called_once_with("project2", self.project2)

    def test_call_eval_project_for_all_projects_when_no_project_specified(
        self, mocker: MockerFixture
    ) -> None:
        """handle_args should call eval_project for all projects when no project is specified."""
        mock_eval = mocker.patch.object(cli, "eval_project")

        args = CliArgs(project=None, config_file_path=".vqu.yaml", update=False)

        cli.handle_args(args, self.projects)

        assert mock_eval.call_count == 2
        mock_eval.assert_any_call("project1", self.project1)
        mock_eval.assert_any_call("project2", self.project2)
