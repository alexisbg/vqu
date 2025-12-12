from contextlib import redirect_stdout
import os
import shlex
import subprocess
import sys
from typing import cast

from packaging.version import InvalidVersion, Version
from termcolor import colored, cprint

from vqu.models import ConfigFileFormat, ConfigFilter, Project


class _InvalidValue:
    """Sentinel class representing an invalid value."""

    pass


_ParsedVersion = str | _InvalidValue | None


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
                version = _parse_captured_version(result.stdout)

                # Store the retrieved version
                if isinstance(version, str):
                    config_filter.result = version

                # Print the version information
                _print_version(version, project.version, config_filter.expression)

                # Print the command if there was an error
                if result.returncode:
                    print(f"    {shlex.join(cmd)}")


def _parse_captured_version(output: str) -> _ParsedVersion:
    """Parses the captured version output.

    Args:
        output (str): The captured output string.
    """
    output = output.strip()
    if output and output.lower() != "null":
        try:
            Version(output)
            return output  # Valid version string
        except InvalidVersion:
            return _InvalidValue()  # Invalid version string

    return None


def _print_version(version: _ParsedVersion, prj_version: str, filter_expr: str) -> None:
    """Prints the version information with appropriate coloring based on its validity.

    Args:
        version (_ParsedVersion): The parsed version value from the configuration file.
        prj_version (str): The expected project version.
        filter_expr (str): The filter expression used to retrieve the version.
    """
    if version is None:
        version_msg = colored("[Value not found]", "red")
    elif isinstance(version, _InvalidValue):
        version_msg = colored("[Invalid version]", "red")
    # The versions differ
    elif version != prj_version:
        version_msg = colored(version, "yellow")
    # The versions match
    else:
        version_msg = colored(version, "green")

    print(f"    {filter_expr} = {version_msg}")


def update_project(name: str, project: Project) -> None:
    """Updates the version numbers in the configuration files for the specified project.

    Args:
        name (str): The name of the project.
        project (Project): The project instance.
    """
    # Retrieve current versions before updating
    eval_project(name, project, print_result=False)

    for config_file in project.config_files:
        # Read the file
        with open(config_file.path, "r") as file:
            content = file.read()

            for config_filter in config_file.filters:
                _validate_update(content, config_file.path, config_filter)

                # Replace the old version with the new version
                content = content.replace(cast(str, config_filter.result), project.version, 1)

        # Write the updated content back to the file
        with open(config_file.path, "w") as file:
            file.write(content)
            cprint(
                f"'{config_file.path}' has been updated to version {project.version}.",
                "green",
            )

    # End with a newline
    print("")


def _validate_update(content: str, path: str, config_filter: ConfigFilter) -> None:
    """Validates the version to be updated.

    Args:
        content (str): The configuration file content.
        path (str): The path to the configuration file.
        config_filter (ConfigFilter): The filter used to retrieve the version.
    """
    # Ensure that a value was retrieved
    if config_filter.result is None:
        raise ValueError(
            f"No value retrieved for expression '{config_filter.expression}' in {path}."
        )

    # Count occurrences of the retrieved value
    count = content.count(config_filter.result)
    if count == 0:
        raise ValueError(f"Value '{config_filter.result}' not found in {path}.")
    elif count > 1:
        raise ValueError(f"Multiple occurrences of value '{config_filter.result}' found in {path}.")
