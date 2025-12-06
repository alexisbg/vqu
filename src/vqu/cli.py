from argparse import ArgumentParser
from contextlib import redirect_stdout
from importlib.metadata import metadata, version
import os
import shlex
import shutil
import subprocess
import sys

from termcolor import colored, cprint

from vqu.json_config_file import load_projects_from_json
from vqu.models import CliArgs, ConfigFileFormat, Project


def main() -> None:
    """Entry point for the version manager script.

    Initializes the application by checking dependencies, parsing command-line arguments,
    loading project configurations, and managing version extraction and updates across
    configuration files.
    """
    try:
        check_yq()

        args = get_cli_args()
        projects = load_projects_from_json(args.config_file_path)
        handle_args(args, projects)
    except Exception as e:
        err = colored("[Error]", "red", attrs=["bold"])
        print(f"{err} {e}")
        exit(1)


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
        usage="%(prog)s [project] [options]",
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
        default=".vqu.json",
        help="Path to the configuration file (default: .vqu.json).",
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
    # Validate --update argument dependency
    if args.update and not args.project:
        raise ValueError("The --update option requires a specific project to be specified.")

    # Handle positional project argument
    if args.project:
        project_obj = projects.get(args.project)
        if not project_obj:
            raise ValueError(f"Project '{args.project}' not found in configuration.")

        # Handle --update
        if args.update:
            update_project(args.project, project_obj)

        # Print the specified project
        eval_project(args.project, project_obj)

    # No arguments: print all projects
    else:
        last_key = list(projects.keys())[-1]
        for k, v in projects.items():
            eval_project(k, v)
            if k != last_key:
                print("")


def eval_project(name: str, project: Project, print_result: bool = True) -> None:
    """Evaluates, stores and prints the project's versions.

    Args:
        name (str): The name of the project.
        project (Project): The project instance.
        print_result (bool): If False, suppresses the output.
    """
    # Redirect output to null if print_result is False
    with redirect_stdout(sys.stdout if print_result else open(os.devnull, "w")):
        expected_version = colored(project.version, "green")
        print(f"{name} {expected_version}")

        for config_file in project.config_files:
            # Skip if the file path does not exist
            if not os.path.exists(config_file.path):
                print(f"  {config_file.path}: [File not found]")
                continue

            print(f"  {config_file.path}:")

            for config_filter in config_file.filters:
                file_format = ConfigFileFormat.to_yq_format(config_file.format)

                # Build and run the yq command
                # fmt: off
                cmd = [
                    "yq", "-p", file_format, "-o", "tsv",
                    config_filter.expression, config_file.path
                ]
                # fmt: on
                result = subprocess.run(cmd, capture_output=True, text=True)

                # Parse version value
                version: str | None = result.stdout.strip()
                if not version or version.lower() == "null":
                    version = None

                # Store the retrieved version
                config_filter.result = version

                # Version value could not be retrieved
                if not version:
                    version = colored("[Value not found]", "red")
                # The versions differ
                elif version != project.version:
                    version = colored(version, "yellow")
                # The versions match
                else:
                    version = colored(version, "green")

                print(f"    {config_filter.expression} = {version}")

                # Print the command if there was an error
                if result.returncode:
                    print(f"    {shlex.join(cmd)}")


def update_project(name: str, project: Project) -> None:
    """Updates the version numbers in the configuration files for the specified project.

    Args:
        name (str): The name of the project.
        project (Project): The project instance.
    """
    # Retrieve current versions before updating
    eval_project(name, project, print_result=False)

    for config_file in project.config_files:
        has_file_error = False

        # Read the file
        with open(config_file.path, "r") as file:
            content = file.read()

            for config_filter in config_file.filters:
                # Ensure that a value was retrieved
                if config_filter.result is None:
                    has_file_error = True
                    raise ValueError(
                        "No value retrieved for expression "
                        + f"'{config_filter.expression}' in {config_file.path}."
                    )

                # Count occurrences of the retrieved value
                count = content.count(config_filter.result)
                if count == 0:
                    has_file_error = True
                    raise ValueError(
                        f"Value '{config_filter.result}' not found in {config_file.path}."
                    )
                elif count > 1:
                    has_file_error = True
                    raise ValueError(
                        f"Multiple occurrences of value '{config_filter.result}' "
                        + f"found in {config_file.path}."
                    )

                # Replace the old version with the new version
                content = content.replace(config_filter.result, project.version, 1)

        if not has_file_error:
            # Write the updated content back to the file
            with open(config_file.path, "w") as file:
                file.write(content)
                cprint(
                    f"'{config_file.path}' has been updated to version {project.version}.",
                    "green",
                )

    # End with a newline
    print("")
