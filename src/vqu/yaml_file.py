import os
from pathlib import Path

import yaml

from vqu.models import Project, RootConfig


def load_projects_from_yaml(path: str) -> dict[str, Project]:
    """Loads projects from the vqu YAML file.

    Args:
        path (str): The path to the YAML file.

    Returns:
        dict[str, Project]: A dictionary mapping project names to their corresponding
            Project instances, loaded from the configuration file.
    """
    with open(path, "r") as file:
        data = yaml.safe_load(file)
        root_config = RootConfig(**data)

        abs_path = Path(path).resolve()
        os.chdir(str(abs_path.parent))

        return root_config.projects
