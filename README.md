# Config Saver

Save and restore critical Windows configuration across VM re-provisions.

Config Saver is a CLI tool that backs up application settings, registry keys,
environment variables, Git repo enlistments, and personalization preferences to a
persistent location (e.g., corporate OneDrive). When a VM is wiped and
re-provisioned, run `config-saver restore` to get back to your working state.

## Quick Start

```bash
# Install
uv sync

# Create your config file (see below)
# Save all configured items
config-saver save --all

# Restore everything (interactive selection)
config-saver restore

# Restore specific items
config-saver restore --items vscode_profile,bashrc
```

## Configuration

Config Saver is driven by a YAML file (`config_saver.yaml`). It searches for
the config in:

1. Current working directory
2. `~/.config/config_saver/`

### Minimal Example

```yaml
backup_root: "C:\\Users\\you\\OneDrive - Corp\\ConfigBackup"

configs:
  vscode_profile:
    handler: file
    description: "VS Code settings"
    source: "%APPDATA%\\Code\\User\\settings.json"
```

### Full Example

```yaml
backup_root: "C:\\Users\\you\\OneDrive - Corp\\ConfigBackup"

configs:
  # --- VS Code profiles ---
  vscode:
    handler: vscode
    description: "VS Code and Insiders profiles"
    variants:
      - code
      - code-insiders

  # --- File-based configs ---

  windows_terminal:
    handler: file
    description: "Windows Terminal settings"
    source: "%LOCALAPPDATA%\\Packages\\Microsoft.WindowsTerminal_8wekyb3d8bbwe\\LocalState\\settings.json"

  kusto_connections:
    handler: file
    description: "Kusto Explorer connection groups"
    source: "%LOCALAPPDATA%\\Kusto.Explorer\\ConnectionGroups.xml"
    hooks:
      post_restore: |
        Write-Host "Import connections in Kusto Explorer: Connections > Import..."

  bashrc:
    handler: file
    description: "Git Bash configuration"
    source: "%USERPROFILE%\\.bashrc"
    additional_files:
      - "%USERPROFILE%\\.bash_profile"
      - "%USERPROFILE%\\.gitconfig"

  # --- Registry settings ---
  explorer_context_menu:
    handler: registry
    description: "Explorer context menu customizations"
    keys:
      - "HKCU\\Software\\Classes\\Directory\\Background\\shell\\MyItem"
      - "HKCU\\Software\\Classes\\Directory\\shell\\MyItem"

  # --- Environment variables ---
  user_env:
    handler: env_vars
    description: "User environment variables"
    scope: user
    exclude_vars:
      - "TEMP"
      - "TMP"

  # --- Git repo enlistments ---
  ado_repos:
    handler: git_repos
    description: "ADO repository enlistments"
    scan_roots:
      - "E:\\src"

  # --- Windows personalization ---
  personalization:
    handler: personalization
    description: "Wallpaper and color scheme"
    settings:
      - wallpaper
      - color_scheme
```

## Configuration Reference

### Top-Level Fields

| Field         | Type   | Required | Description                                      |
|---------------|--------|----------|--------------------------------------------------|
| `backup_root` | string | Yes      | Path to backup destination (supports `%ENV_VAR%`) |
| `configs`     | map    | No       | Map of config item name → config item definition  |

### Config Item Fields

Every config item requires a `handler` field. Other fields depend on the handler.

| Field         | Type   | Description                                |
|---------------|--------|--------------------------------------------|
| `handler`     | string | Handler type (see below)                   |
| `description` | string | Human-readable description                 |
| `hooks`       | object | Pre/post save/restore commands (see Hooks) |

### Handlers

#### `vscode` — VS Code / Insiders full profile

| Field      | Type            | Description                                        |
|------------|-----------------|----------------------------------------------------|
| `variants` | list of strings | Which editors: `code`, `code-insiders` (default: `code`) |

Saves settings.json, keybindings.json, snippets/, globalStorage/, and the
full extensions/ folder. Extensions are copied as-is (no marketplace needed).
Config files go through normal latest + archive; extensions use a single
dedicated folder at `<backup_root>/vscode_extensions/<variant>/` to avoid
archiving large extension data.

#### `file` — Copy files to/from backup

| Field              | Type            | Description                                    |
|--------------------|-----------------|------------------------------------------------|
| `source`           | string or list  | File path(s) to back up (supports `%ENV_VAR%`) |
| `additional_files` | list of strings | Extra files to include                         |

#### `registry` — Export/import Windows registry keys

| Field  | Type            | Description                                      |
|--------|-----------------|--------------------------------------------------|
| `keys` | list of strings | Registry key paths to export (e.g. `HKCU\\...`) |

#### `env_vars` — Save/restore user environment variables

| Field          | Type            | Description                                          |
|----------------|-----------------|------------------------------------------------------|
| `scope`        | string          | `user` (default) or `system`                         |
| `include_vars` | list of strings | Only save these variables (default: all)             |
| `exclude_vars` | list of strings | Skip these variables (e.g. `TEMP`, `TMP`)            |

#### `git_repos` — Scan and record Git repo enlistments

| Field        | Type            | Description                                           |
|--------------|-----------------|-------------------------------------------------------|
| `scan_roots` | list of strings | Root directories to recursively scan for `.git` repos |

#### `personalization` — Windows wallpaper and color scheme

| Field      | Type            | Description                                             |
|------------|-----------------|---------------------------------------------------------|
| `settings` | list of strings | Which settings to capture (`wallpaper`, `color_scheme`) |

### Hooks

Each config item can define shell commands to run at specific points:

```yaml
hooks:
  pre_save: "echo About to save"
  post_save: "echo Save complete"
  pre_restore: "echo About to restore"
  post_restore: "echo Restore complete"
```

Hook commands are executed via PowerShell. They fail gracefully (warnings only).

## CLI Commands

```
config-saver save [--all | --items ITEMS]     Save configs to backup
config-saver restore [--all | --items ITEMS]  Restore configs from backup
config-saver list                             List configured items and status
config-saver diff                             Compare current state with backup
```

When run without a subcommand, an interactive menu is presented.

### Options

| Flag            | Description                                  |
|-----------------|----------------------------------------------|
| `--config PATH` | Path to config YAML (default: auto-discover) |
| `--all`         | Save/restore all configured items            |
| `--items A,B,C` | Save/restore only the named items            |
| `--dry-run`     | Preview changes without applying (restore)   |
| `--archive TS`  | Restore from a specific archived backup      |

## Backup Storage

Backups are stored in the `backup_root` directory with this structure:

```
<backup_root>/
  latest/                          # Always the most recent backup
    vscode_profile/
      settings.json
    bashrc/
      .bashrc
      .bash_profile
    explorer_context_menu/
      key1.reg
    ...
  archive/
    2026-03-04T10-30-00/           # Timestamped snapshots
      vscode_profile/
        settings.json
      ...
```

Each `save` operation updates `latest/` and creates a timestamped copy in
`archive/`.

## Adding Custom Handlers

Config Saver is extensible. To add a new handler:

1. Create a new file in `config_saver/handlers/` (e.g., `my_handler.py`)
2. Subclass `BaseHandler` and implement `save()` and `restore()`:

```python
from config_saver.handlers.base import BaseHandler

class MyHandler(BaseHandler):
    """Handle my custom config type."""

    name = "my_handler"

    def save(self, item_name, config_item, store):
        # Save logic here
        ...

    def restore(self, item_name, config_item, store):
        # Restore logic here
        ...
```

3. Register it in `config_saver/handlers/__init__.py`
4. Use `handler: my_handler` in your YAML config

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
pytest

# Lint and format
ruff check config_saver tests --fix
ruff format config_saver tests

# Type checking
mypy config_saver
```

## Path Variable Expansion

All paths in the YAML config support environment variable expansion:

- Windows style: `%APPDATA%`, `%USERPROFILE%`, `%LOCALAPPDATA%`
- Unix style: `$HOME`, `${HOME}`
- Tilde: `~/` expands to user home directory
