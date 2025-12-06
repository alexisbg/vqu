import json
import os
from pathlib import Path

from vqu.models import Project, RootConfig


def load_projects_from_json(path: str) -> dict[str, Project]:
    """Loads projects from the JSON configuration file.

    Args:
        path (str): The file path to the JSON configuration file.

    Returns:
        dict[str, Project]: A dictionary mapping project names to their corresponding
            Project instances, loaded from the configuration file.
    """
    with open(path, "r") as file:
        data = json.load(file)

        abs_path = Path(path).resolve()
        os.chdir(str(abs_path.parent))

        root_config = RootConfig.from_dict(data)

        return root_config.projects
