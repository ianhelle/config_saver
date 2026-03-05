"""Built-in configuration handlers."""

# Import all handlers to trigger auto-registration
from config_saver.handlers.env_vars import EnvVarsHandler
from config_saver.handlers.file import FileHandler
from config_saver.handlers.git_repos import GitReposHandler
from config_saver.handlers.personalization import PersonalizationHandler
from config_saver.handlers.registry import RegistryHandler
from config_saver.handlers.vscode import VSCodeHandler

__all__ = [
    "EnvVarsHandler",
    "FileHandler",
    "GitReposHandler",
    "PersonalizationHandler",
    "RegistryHandler",
    "VSCodeHandler",
]
