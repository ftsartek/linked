from os import getenv
from pathlib import Path
from typing import Any

from msgspec import Struct
from msgspec.yaml import decode as yaml_decode


class ConfigLoader[T: Struct]:
    """
    Generic configuration manager.
    """

    def __init__(
        self,
        mapped_class: type[T],
        source_file: Path,
        source_override_env: str | None = None,
        raise_on_missing: bool = False,
    ) -> None:
        self._mapped_class = mapped_class
        loaded_env = None
        if source_override_env and getenv(source_override_env):
            loaded_env = getenv(source_override_env)
        self._source_file = Path(loaded_env) if loaded_env else source_file
        self._source_override_env = source_override_env
        self._raise_on_missing = raise_on_missing
        self._config = None

    def _load_config(self) -> T:
        """
        Generic configuration loader that works with any ConfigBase subclass.

        Returns:
            Tuple of (config_instance, loaded_file_path)
        """
        if self._source_file.exists():
            with self._source_file.open("rb") as f:
                data = f.read()
                return self._decode_yaml(data, self._mapped_class)
        if self._raise_on_missing:
            raise FileNotFoundError(f"Config file not found at {self._source_file}")

        return self._mapped_class()

    def get_config(self) -> T:
        if not self._config:
            self._config = self._load_config()
        return self._config

    @staticmethod
    def _decode_yaml(data: str | bytes, model_type: Any) -> T:
        return yaml_decode(data, type=model_type, strict=False)
