import logging
from pathlib import Path
import shlex
import subprocess
from typing import cast

from termcolor import colored

from vqu.logger import output_logger
from vqu.models import ConfigFileFormat, ConfigFilter, Project


def eval_project(name: str, project: Project, print_result: bool = True) -> None:
    """Evaluates, stores and prints the project's versions.

    Args:
        name (str): The name of the project.
        project (Project): The project instance.
        print_result (bool): If False, suppresses the output.
    """
    # Suppress output if print_result is False
    if not print_result:
        # output_logger.disabled = True
        output_logger.setLevel(logging.CRITICAL)

    try:
        expected_version = colored(project.version, "green")
        output_logger.info(f"{name} {expected_version}")

        for config_file in project.config_files:
            # Skip if the file path does not exist
            if not Path(config_file.path).exists():
                file_not_found = colored("[File not found]", "red")
                output_logger.warning(f"  {config_file.path}: {file_not_found}")
                continue

            output_logger.info(f"  {config_file.path}:")

            file_format = ConfigFileFormat.to_yq_format(config_file.format)

            for config_filter in config_file.filters:
                # Build and run the yq command
                # fmt: off
                cmd = [
                    "yq", "-p", file_format, "-o", "tsv",
                    config_filter.expression, config_file.path
                ]
                # fmt: on
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                version_output: str | None = None
                if not result.returncode:
                    version_output = result.stdout.strip() or None

                # The setter validates the provided value
                config_filter.result = version_output
                _print_version(config_filter, project.version)

                # Print the command if there was an error
                if result.returncode:
                    output_logger.warning(f"    {shlex.join(cmd)}")
    finally:
        # Restore logger level
        output_logger.setLevel(logging.INFO)


def _print_version(config_filter: ConfigFilter, prj_version: str) -> None:
    """Prints the version information with appropriate coloring based on its validity.

    Args:
        config_filter (ConfigFilter): The configuration filter instance.
        prj_version (str): The expected project version.
    """
    if config_filter.invalid_result is not None:
        version_msg = colored(f"[Invalid version] {config_filter.invalid_result}", "red")
    elif config_filter.result is None:
        version_msg = colored("[Value not found]", "red")
    # The versions differ
    elif config_filter.result != prj_version:
        version_msg = colored(config_filter.result, "yellow")
    # The versions match
    else:
        version_msg = colored(config_filter.result, "green")

    output_logger.info(f"    {config_filter.expression} = {version_msg}")


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

        original_content = content
        for config_filter in config_file.filters:
            if config_filter.result != project.version:
                _validate_update(content, config_file.path, config_filter)

                # Replace the old version with the new version
                content = content.replace(cast(str, config_filter.result), project.version, 1)

        # Write the updated content back to the file
        if content != original_content:
            with open(config_file.path, "w") as file:
                file.write(content)
                success = colored(
                    f"{config_file.path!r} has been updated to version {project.version}.", "green"
                )
                output_logger.info(success)

    # End with a newline
    output_logger.info("")


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
            f"No value retrieved for expression {config_filter.expression!r} in {path}."
        )

    # Count occurrences of the retrieved value
    count = content.count(config_filter.result)
    if count == 0:
        raise ValueError(f"Value {config_filter.result!r} not found in {path}.")
    elif count > 1:
        raise ValueError(f"Multiple occurrences of value {config_filter.result!r} found in {path}.")
