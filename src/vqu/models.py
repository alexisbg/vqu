from enum import Enum

from pydantic import BaseModel, ConfigDict
from pydantic.fields import Field


class CliArgs(BaseModel):
    """Data container for CLI arguments.

    Attributes:
        project (str | None): Select a specific project.
        config_file_path (str): The path to the configuration file.
        update (bool): Write the version numbers to the configuration files. Requires
            that the project attribute is set.
    """

    project: str | None
    config_file_path: str
    update: bool


class RootConfig(BaseModel):
    """Data container for the vqu YAML file of this script.

    Attributes:
        projects (dict[str, Project]): A dictionary mapping project names to their corresponding
            Project instances, loaded from the configuration file.
    """

    projects: dict[str, "Project"]


class Project(BaseModel):
    """Data container for a project entry.

    Attributes:
        version (str): The current version of the project.
        config_files (list[ConfigFile]): List of configuration files associated with this project
            that contain version numbers managed by this script.
    """

    model_config = ConfigDict(populate_by_name=True)

    version: str = Field(..., min_length=1)
    config_files: list["ConfigFile"]


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
    format: "ConfigFileFormat"
    filters: list["ConfigFilter"]


class ConfigFilter(BaseModel):
    """Data container for a configuration filter entry.

    Attributes:
        expression (str): The yq command syntax string used to extract or update the version value.
        result (str | None): The extracted version value, or None if not yet retrieved.
    """

    expression: str = Field(min_length=1)
    result: str | None = None


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
    def to_yq_format(cls, value: "ConfigFileFormat") -> str:
        """Convert some enum values to the corresponding yq format string."""
        conversion_map: dict[ConfigFileFormat, str] = {
            ConfigFileFormat.DOTENV: "props",
        }

        return conversion_map.get(value, value.value)
