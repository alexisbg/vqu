from __future__ import annotations

from enum import Enum
import re
from typing import Any

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field


class CliArgs(BaseModel):
    """Data container for CLI arguments.

    Attributes:
        project (str | None): Select a specific project.
        config_file_path (str): The path to the configuration file.
        update (bool): Write the version numbers to the configuration files. Requires
            that the project attribute is set.
    """

    project: str | None = None
    config_file_path: str
    update: bool


class RootConfig(BaseModel):
    """Data container for the vqu YAML file of this script.

    Attributes:
        projects (dict[str, Project]): A dictionary mapping project names to their corresponding
            Project instances, loaded from the configuration file.
    """

    projects: dict[str, Project]


class Project(BaseModel):
    """Data container for a project entry.

    Attributes:
        version (str): The current version of the project.
        config_files (list[ConfigFile]): List of configuration files associated with this project
            that contain version numbers managed by this script.
    """

    version: str = Field(..., min_length=1)
    config_files: list[ConfigFile]


class ConfigFile(BaseModel):
    """Data container for a configuration file entry.

    Attributes:
        path (str): Filesystem path to the configuration file, relative to this script.
        format (ConfigFileFormat): The configuration file format; expected to match a member
            of the `ConfigFileFormat` enum.
        filters (list[ConfigFilter]): List of yq command syntax strings used to extract the version
            value from this configuration file.
    """

    path: str = Field(..., min_length=1)
    format: ConfigFileFormat
    filters: list[ConfigFilter]


class ConfigFilter(BaseModel):
    """Data container for a configuration filter entry.

    Attributes:
        expression (str): The yq command syntax string used to extract or update the version value.
        invalid_result (str | None): The raw extracted value that failed validation. None if result
            is valid.
        result (str | None): The extracted version value, or None if not yet retrieved.
        validate_docker_tag (bool | None): Whether to validate the result as a valid Docker tag.
        validate_regex (str | None): A regex pattern to validate the result against.
    """

    model_config = ConfigDict(validate_assignment=True)

    expression: str = Field(..., min_length=1)
    invalid_result: str | None = None
    result: str | None = None
    validate_docker_tag: bool | None = None
    validate_regex: str | None = Field(default=None, min_length=1)

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401
        """Override __setattr__ to validate the 'result' attribute.

        When setting 'result', if the value is invalid, sets 'result' to None
        and stores the invalid value in 'invalid_result'.

        Args:
            name (str): The attribute name.
            value (Any): The value to set.
        """
        # Pydantic validate the type and set the value first
        super().__setattr__(name, value)

        if name == "result":
            # Clear invalid_result when result is set
            super().__setattr__("invalid_result", None)

            # Skip if value is None
            if value is None:
                return

            is_valid = True

            # Not an empty string or contains null string
            if not value or value.lower() == "null":
                super().__setattr__("result", None)
                return

            # Validate as Docker tag if provided
            elif self.validate_docker_tag:
                if not re.fullmatch(r"[\w][\w.-]{0,127}", value):
                    is_valid = False

            # Validate against regex if provided
            elif self.validate_regex:
                if not re.fullmatch(self.validate_regex, value):
                    is_valid = False

            # Validate as Python packaging version
            else:
                try:
                    Version(value)
                except InvalidVersion:
                    is_valid = False

            if not is_valid:
                # Set result to None and store invalid value
                super().__setattr__("invalid_result", value)
                super().__setattr__("result", None)


class ConfigFileFormat(str, Enum):
    """Enumeration of supported configuration file formats."""

    DOTENV = "dotenv"
    JSON = "json"
    TOML = "toml"
    XML = "xml"
    YAML = "yaml"

    @classmethod
    def has_value(cls, value: str) -> bool:
        """Check if the enum contains a member with the specified value."""
        return value in cls._value2member_map_

    @classmethod
    def to_yq_format(cls, value: ConfigFileFormat) -> str:
        """Convert some enum values to the corresponding yq format string."""
        conversion_map: dict[ConfigFileFormat, str] = {
            cls.DOTENV: "props",
        }

        return conversion_map.get(value, value.value)
