import json
from configparser import ConfigParser, ExtendedInterpolation
import os
from typing import Any, Dict, List, Iterator

from mindtrace.utils import ifnone


class Config:
    """Mtrix Config.

    To use the config parser, fill out the *config.ini* file. It includes paths to local directories as well as API keys
    necessary to use some services, such as OpenAI (ChatGPT) or the Discord Client.
    This class loads and manages configuration settings from multiple sources, applying a precedence rule.

    Some notes to help you:
        1. API keys are required by most services. Refer to the services documentation for more information.
        2. You may use tildes (~) to denote the user home directory in the config file.
        3. The config file may refer to other parts of itself using ${}. Refer to the config file itself for examples.
        4. Most demos / scripts that ask for a resource path can be left blank if the config has the associated info.

    Args:
        config_path: The complete path to the .ini file. If `None`, it:
            1. Checks `MtrixConfig` environment variable for a file path and loads it.
            2. Loads default `config.ini` in the core directory.

    **Configuration Precedence (Highest to Lowest Priority)**:

    1. **Environment Variables**: If a matching environment variable is set, it **overrides** the config file value.
       - Format: `{SECTION}__{KEY}` (e.g., `MTRIX__ROOT_DIR` for `[MTRIX] ROOT_DIR` in ini file)
       - If the value starts with `~`, it is expanded to the user's home directory.

    2. **User-defined Configuration File (`.ini`)**: User defined Configuration file can be passed as an argument, if not provided file path defined in `MtrixConfig` environment variable is loaded.

    3. **Default Configuration File (`config.ini`)**: If no overrides exist, values are taken from `config.ini`.


    Default `.ini` File (`config.ini`):
    ```
    [MINDTRACE]
    ROOT = ~/.cache/mindtrace
    DATA = ${DIR_PATHS:ROOT}/data
    ```

    Example::

        from mindtrace import Config

        # Load the configuration
        config = Config()
        root = config["DIR_PATHS"]["ROOT"]  # "~/.cache/mindtrace" by default

        config = Config().as_dict()  # May use Config.__str__() or Config.as_dict() for serializable operations
        print(json.dumps(config, indent=4))
    """

    def __init__(self, config_path: str = None):
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.config.optionxform = str  # Maintain case sensitivity

        # Default config file (Lowest priority)
        default_config_path = os.path.join(os.path.dirname(__file__), "config.ini")

        # User-defined config (Higher priority)

        user_config_path = ifnone(config_path, os.environ.get("MtrixConfig"))

        # Step 1️ Load default config first
        if os.path.exists(default_config_path):
            self.config.read(default_config_path)

        # Step 2️ Overlay user-defined config, if exists
        if user_config_path:
            if os.path.exists(user_config_path):
                user_config = ConfigParser(interpolation=ExtendedInterpolation())
                user_config.optionxform = str
                user_config.read(user_config_path)

                # Merge user-defined values on top of the default ones
                for section in user_config.sections():
                    if not self.config.has_section(section):
                        self.config.add_section(section)
                    for key, value in user_config.items(section):
                        self.config.set(section, key, value)
            else:
                raise FileNotFoundError(f"User-defined config file not found at path: {user_config_path}")

        # Step 3️ Expand `~` for final selected values
        for section in self.config.sections():
            for k, v in self.config.items(section):
                if v.startswith("~"):
                    self.config[section][k] = v.replace("~", os.path.expanduser("~"))

    def __getitem__(self, section: str) -> Dict[str, Any]:
        if section not in self.config:
            raise KeyError(f'Section "{section}" not found in the configuration.')
        # Return a dictionary-like object that handles environment variable overrides
        return _ConfigSection(self.config, section)

    def __contains__(self, section: str) -> bool:
        """Check if a section exists in the config."""
        return section in self.config

    def __iter__(self) -> Iterator[str]:
        """Iterate over section names."""
        return iter(self.config.sections())

    def keys(self) -> List[str]:
        """Return a list of section names."""
        return self.config.sections()

    def items(self):
        """Return a list of (section_name, section_dict) pairs."""
        return [(section, self[section]) for section in self.config.sections()]

    def get(self, section: str, default=None):
        """Get a section if it exists, otherwise return default."""
        try:
            return self[section]
        except KeyError:
            return default

    def __str__(self) -> str:
        return json.dumps({section: dict(self.config[section]) for section in self.config.sections()}, indent=4)

    def as_dict(self) -> Dict:
        return json.loads(str(self))

    def pretty_print(self) -> str:
        return json.dumps(self.as_dict(), indent=4)


class _ConfigSection:
    """Helper class to resolve environment variable overrides dynamically."""

    def __init__(self, config: ConfigParser, section: str):
        self.config = config
        self.section = section

    def __getitem__(self, key: str) -> Any:
        """Fetch a value, applying the precedence rules."""
        env_var = f"{self.section}__{key}".upper()  # Convert section.key to ENV variable format

        # 1. Check environment variable (highest priority)
        if env_var in os.environ:
            val = os.environ[env_var]
            return val.replace("~", os.path.expanduser("~")) if val.startswith("~") else val

        # 2. Check user-defined configuration file (MtrixConfig) if it exists
        if key in self.config[self.section]:
            return self.config[self.section][key]

        # 3. If key is missing in both, raise an error
        raise KeyError(f'Key "{key}" not found in section "{self.section}".')

    def items(self):
        """Return section items as key-value pairs."""
        return self.config.items(self.section)

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in this section."""
        env_var = f"{self.section}__{key}".upper()
        return env_var in os.environ or key in self.config[self.section]

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys in this section."""
        return iter(self.config[self.section])

    def keys(self) -> List[str]:
        """Return a list of keys in this section."""
        return list(self.config[self.section].keys())

    def get(self, key: str, default=None):
        """Get a value if it exists, otherwise return default."""
        try:
            return self[key]
        except KeyError:
            return default
