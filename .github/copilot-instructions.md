# Copilot Instructions for Config Saver

## Project Overview

This is **config-saver** — a CLI tool that saves and restores critical Windows
configuration data (VS Code settings, Windows Terminal, registry keys, PATH, Git
Bash rc files, Kusto connections, ADO repo enlistments, and personalization
settings) to a persistent location (e.g., OneDrive) for re-provisioned VMs.

## Development Setup

### Installation
```bash
uv sync --extra dev
```

### Package Structure
- **Package name**: `config-saver` (in `config_saver/`)
- **Import pattern**: `from config_saver import <module>`
- **Source**: `config_saver/` contains implementation modules
- **Tests**: `tests/` with pytest markers: `unit`, `integration`

## Code Conventions

### Python Standards (Enforced by Ruff)
- **Line length**: 93 characters
- **Type hints**: Required (enforced by mypy, annotations checked)
  Always use built-in types like list,
  dict, for type annotations and avoid use types from `typing`. E.g. use `list[str]`
  instead of `List[str]`, `str | None` instead of `Optional[str]`.
- **Docstrings**: Required for public functions (D-series rules) - use numpy style.
  Document parameters, return type and exceptions raised for public functions/methods.
  - **Single-line**: Keep on same line as triple quotes: `"""Return the user name."""`
  - **Multi-line**: Summary starts on new line after opening quotes, blank line before
    Parameters/Returns sections, blank line before closing quotes:
    ```python
    def example(name: str) -> str:
        """
        Return a greeting for the given name.

        Parameters
        ----------
        name : str
            The name to greet.

        Returns
        -------
        str
            The greeting message.

        """
    ```
- **Imports and Formatting**: Sorted/grouped automatically (isort)

### General Coding Style
- Avoid using Python built-in `open` function for file operations. Use `pathlib.Path`
  methods instead. Prefer Path.* methods over legacy os.* methods.
- Logging — If adding logging calls, use %s, %d style variable substitution rather than
  f-strings.
- Never use inline import statements. Always place imports at the top of the file.
- When generating code, be careful with indentation — always replace lines using the
  same indentation unless introducing branches, etc.
- Never exceed a line length of 90 characters — this applies to code, docstrings,
  comments and suppressions.

### Pydantic over Dataclasses and Complex Data Structures
- **Always use Pydantic `BaseModel`** instead of `@dataclass` for data classes.
- **Always use Pydantic models for complex data structures** instead of
  nested dicts/lists/tuples. This provides type safety, validation and serialization.
- Use `ConfigDict(extra="ignore")` for forward compatibility.
- Use `model_dump(mode="json")` for serialization instead of custom `to_dict()` methods.
- Use `model_validate()` for deserialization instead of custom `from_dict()` methods.
- Use `PrivateAttr` for internal state that shouldn't be serialized.
- For post-initialization logic, use `model_post_init()` instead of `__post_init__`.

## Testing

### Test Creation
- Always use pytest and generate pytest-style test functions.
- Test file modules should mirror the name/path of the tested module, e.g.
  `config_saver/handlers/file.py` → `tests/handlers/test_file.py`
- Always add at least a single-line docstring to fixtures and test functions.
  If the context of the parameters is not obvious, explain them in the docstring.

### Running Tests
```bash
pytest                           # All tests
pytest -m unit                   # Unit tests only
pytest -m integration            # Integration tests
pytest --cov=config_saver --cov-report=html
```

### Test Markers
- `@pytest.mark.unit` — Fast, isolated tests
- `@pytest.mark.integration` — Tests requiring external services

## Code Quality Tools

### Running Linters
```bash
ruff check config_saver --fix     # Lint and auto-fix
ruff format config_saver          # Format code
mypy config_saver                 # Type checking
```

**Important**: When running mypy, always run it to get the full output. It is slow, so
avoid preliminary runs to find error counts — run it once completely.

### When Generating New Python Code
**ALWAYS run linter checks after generating new Python code:**
```bash
ruff check config_saver --fix && ruff format config_saver && mypy config_saver
```

Fix any errors before committing. Do not leave Ruff or mypy errors in generated code.

## Commit Guidelines
- Write clear, descriptive commit messages.
- Always run linters before committing.
- Create a commit once a feature is complete.

## Key Files

- **`pyproject.toml`**: Package config, dependencies, tool settings (ruff, mypy, pytest)
- **`config_saver/models.py`**: Pydantic models for the YAML config schema
- **`config_saver/handlers/`**: Pluggable handler classes for each config type
- **`config_saver/cli.py`**: Click-based CLI entry point
- **`config_saver/store.py`**: Backup store (latest + timestamped archive)
