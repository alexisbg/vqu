from argparse import ArgumentParser
from importlib.metadata import metadata, version
import shutil
import sys

from termcolor import colored

from vqu.logger import output_logger
from vqu.models import CliArgs, Project
from vqu.project import eval_project, update_project
from vqu.yaml_file import load_projects_from_yaml


def main() -> None:
    """Entry point for the version manager script.

    Initializes the application by checking dependencies, parsing command-line arguments,
    loading project configurations, and managing version extraction and updates across
    configuration files.
    """
    try:
        check_yq()

        args = get_cli_args()
        projects = load_projects_from_yaml(args.config_file_path)
        handle_args(args, projects)
    except Exception as e:
        err = colored("[Error]", "red", attrs=["bold"])
        output_logger.critical(f"{err} {e}")
        sys.exit(1)


def check_yq() -> None:
    """Checks if the 'yq' command is installed on the system.

    Raises:
        FileNotFoundError: If 'yq' is not found in the system's PATH.
    """
    # noinspection PyDeprecation
    yq_path = shutil.which("yq")
    if not yq_path:
        raise FileNotFoundError("'yq' command not found. Please install 'yq' to proceed.")


def get_cli_args() -> CliArgs:
    """Parses and returns the command-line arguments.

    Returns:
        CliArgs: An instance of CliArgs containing the parsed arguments.
    """
    parser = ArgumentParser(
        "vqu",
        description=metadata("vqu")["Summary"],
        # usage="%(prog)s [project] [options]",
        add_help=False,
    )

    # fmt: off
    parser.add_argument(
        "project",
        nargs="?",
        help="The name of the project to display versions for.",
    )
    parser.add_argument(
        "-c", "--config",
        metavar="PATH",
        default=".vqu.yaml",
        help="Path to the configuration file (default: .vqu.yaml).",
    )
    parser.add_argument(
        "-u", "--update",
        action="store_true",
        help="Write the version numbers in the configuration files.",
    )
    parser.add_argument(
        "-h", "--help",
        action="help",
        help="Show this help message and exit.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"{parser.prog} {version('vqu')}",
        help="Show the version and exit.",
    )
    # fmt: on

    args = parser.parse_args()

    # Validate --update requires project
    if args.update and not args.project:
        parser.error("The --update option requires a project to be specified.")

    return CliArgs(
        project=args.project,
        config_file_path=args.config,
        update=args.update,
    )


def handle_args(args: CliArgs, projects: dict[str, Project]) -> None:
    """Handles the CLI arguments and performs the corresponding actions.

    Args:
        args (CliArgs): The parsed command-line arguments.
        projects (dict[str, Project]): A dictionary mapping project names to their corresponding
            Project instances, loaded from the configuration file.
    """
    # Handle positional project argument
    if args.project:
        project_obj = projects.get(args.project)
        if not project_obj:
            raise ValueError(f"Project {args.project!r} not found in configuration.")

        # Handle --update
        if args.update:
            update_project(args.project, project_obj)

        # Print the specified project
        eval_project(args.project, project_obj)

    # No arguments: print all projects
    else:
        for i, (k, v) in enumerate(projects.items()):
            if i > 0:
                output_logger.info("")
            eval_project(k, v)
