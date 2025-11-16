import os
from typing import Any, Dict, Optional


class SettingsLoader:
    _instance: Optional["SettingsLoader"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._config: Dict[str, Any] = {}
            self._load_config()
            self._initialized = True

    def _load_config(self):
        default_config = {
            "data_dir": "data",
            "rates_ttl_seconds": 300,
            "default_base_currency": "USD",
            "log_dir": "logs",
            "log_level": "INFO",
            "log_format": "json",
            "max_log_size_mb": 10,
            "backup_count": 5,
        }

        try:
            import toml
            pyproject_path = "pyproject.toml"
            if os.path.exists(pyproject_path):
                with open(pyproject_path, "r") as f:
                    pyproject_data = toml.load(f)

                valuta_config = pyproject_data.get("tool", {}).get("valutatrade", {})
                default_config.update(valuta_config)
        except ImportError:
            pass
        except Exception:
            pass

        for key in default_config:
            env_key = f"VALUTATRADE_{key.upper()}"
            if env_key in os.environ:
                value = os.environ[env_key]
                if isinstance(default_config[key], bool):
                    default_config[key] = value.lower() in ("true", "1", "yes")
                elif isinstance(default_config[key], int):
                    default_config[key] = int(value)
                elif isinstance(default_config[key], float):
                    default_config[key] = float(value)
                else:
                    default_config[key] = value

        self._config = default_config

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def reload(self):
        self._initialized = False
        self.__init__()

    def __getitem__(self, key: str) -> Any:
        return self._config[key]

    def __contains__(self, key: str) -> bool:
        return key in self._config


settings = SettingsLoader()
