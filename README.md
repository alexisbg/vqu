# vqu

`vqu` is a command-line tool for querying and updating version numbers across multiple configuration
files in your projects. It allows you to:

- **Query** version information from .env, JSON, TOML, XML, and YAML configuration files
- **Compare** versions across different files to ensure consistency
- **Update** version numbers simultaneously in all configured files with a single command

`vqu` uses [yq](https://github.com/mikefarah/yq) syntax to locate and extract version values from
your configuration files. This means you can use powerful query expressions like `.version`,
`.project.version`, or `.metadata[0].version` to precisely target version fields regardless of file
format or nesting depth.

This is particularly useful for monorepos and projects that maintain version information across
multiple configuration formats. Instead of manually updating each file, `vqu` automates the process
and validates that all versions are consistent.

## Requirements

### System
- [yq](https://github.com/mikefarah/yq?tab=readme-ov-file#install) must be installed on your system.

### Python
- `vqu` requires Python 3.10 or later.
- Runs on macOS, Windows, and all Linux distributions.

## Installation
`vqu` can be installed using `pip`:
```
pip install vqu
```

## YAML File Structure

By default, vqu looks for a `.vqu.yaml` configuration file in the current directory. Here's an
example of the configuration structure:

```yaml
projects:
  Project_1:
    version: 0.1.1
    config_files:
      - path: proj1/.env
        format: dotenv
        filters:
          - expression: .VERSION
      - path: proj1/conf.json
        format: json
        filters:
          - expression: .project.version
  Project_2:
    version: 0.1.3
    config_files:
      - path: proj2/conf.yaml
        format: yaml
        filters:
          - expression: .project.version
  Nginx_Service:
    version: stable-alpine3.21
    config_files:
      - path: compose.yaml
        format: yaml
        filters:
          - expression: .services.service2.image | split(":")[1]
            validate_docker_tag: true
      - path: proj2/conf.xml
        format: xml
        filters:
          - expression: .Project.ImageTag
            validate_regex: "[\\w.-]{1,50}"
```

### Schema

**Root level:**
- `projects` (required) - Object containing one or more project definitions. Keys are arbitrary
project names.

**Project object:**
- `version` (required) - The expected version number for this project (e.g., `"0.1.1"`).
- `config_files` (required) - Array of configuration files to manage for this project.

**Configuration file object:**
- `path` (required) - Path to the configuration file, relative to the `.vqu.yaml` file.
- `format` (required) - File format. Supported formats: `dotenv`, `json`, `toml`, `xml`, `yaml`.
- `filters` (required) - Array of filter objects that extract version values from this file.

**Filter object:**
- `expression` (required) - A [yq query expression](https://mikefarah.gitbook.io/yq) that targets a
version value in the configuration file (e.g., `.version`, `.project.version`, `.[0].version`).
- `validate_docker_tag` (optional) - Boolean flag to validate extracted value as valid Docker tag
format. When set to `true`, value must match Docker tag naming rules
(e.g., `"stable-alpine3.21"`, `"11-noble"`).
- `validate_regex` (optional) - A regex pattern to validate extracted value against. Entire
value must match the provided pattern (e.g., `"v\\d+\\.\\d+\\.\\d+"` for semantic versioning with
'v' prefix).


## Example

If you've downloaded or cloned the repository from [GitHub](https://github.com/alexisbg/vqu), you
can try the example configuration:
```bash
vqu -c ./examples/.vqu.yaml
```

This will output version information for all configured projects with color-coded status:

<img src="https://github.com/alexisbg/vqu/raw/main/.github/images/vqu_example.webp" alt="vqu example output" width="530" style="width: 530px">
<!-- <img src=".github/images/vqu_example.webp" alt="vqu example output" width="530" style="width: 530px"> -->

**Color legend:**
- 🟢 Version matches the expected project version
- 🟡 Version differs from the expected project version
- 🔴 Value not found or invalid version format

## Command line usage
```
usage: vqu [project] [options]

Query and update version numbers across multiple configuration files.

positional arguments:
  project               The name of the project to display versions for.

options:
  -c PATH, --config PATH
                        Path to the configuration file (default: .vqu.yaml).
  -u, --update          Write the version numbers in the configuration files.
  -h, --help            Show this help message and exit.
  -v, --version         Show the version and exit.
```

## License
This project is licensed under the terms of the MIT license.
