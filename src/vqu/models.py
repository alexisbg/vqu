from __future__ import annotations

from enum import Enum
import re

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


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
        result (str | None): The extracted version value, or None if not yet retrieved.
        validate_docker_tag (bool | None): Whether to validate the result as a valid Docker tag.
        validate_regex (str | None): A regex pattern to validate the result against.
    """

    model_config = ConfigDict(validate_assignment=True)

    expression: str = Field(..., min_length=1)
    result: str | None = None
    validate_docker_tag: bool | None = None
    validate_regex: str | None = Field(default=None, min_length=1)

    @field_validator("result", mode="after")
    @classmethod
    def validate_result(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Validates the result attribute based on the other attributes if set.

        Args:
            value (str | None): The result value to validate.
            info (ValidationInfo): Additional validation information.

        Returns:
            str | None: The validated result value.

        Raises:
            ValueError: If the result does not pass the specified validations.
        """
        # Pydantic checks if value is a string or None before calling this validator
        if value is None:
            return value

        # Not an empty string or contains null string
        if not value or value.lower() == "null":
            return None

        # Validate as Docker tag
        elif info.data.get("validate_docker_tag"):
            if not re.fullmatch(r"[\w][\w.-]{0,127}", value):
                raise ValueError(f"Filter result {value!r} is not a valid Docker tag.")

        # Validate against regex if provided
        elif info.data.get("validate_regex"):
            if not re.fullmatch(info.data["validate_regex"], value):
                raise ValueError(
                    f"Filter result {value!r} does not match the regex pattern "
                    + f"{info.data['validate_regex']!r}."
                )

        # Validate as Python packaging version
        else:
            try:
                Version(value)
            except InvalidVersion:
                raise ValueError(f"Filter result {value!r} is not a valid version string.")

        return value


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
