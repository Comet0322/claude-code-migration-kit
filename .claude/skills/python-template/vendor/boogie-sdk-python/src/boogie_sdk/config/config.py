"""BoogieConfig: immutable configuration loaded from a YAML file + env overrides.

See boogie-sdk-api.md (this skill's library doc) section 4 (共用慣例).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

_ENV_PREFIX = "BOOGIE_"
_DEFAULT_CONFIG_FILE = "boogie_sdk.yaml"


@dataclass(frozen=True)
class BoogieConfig:
    """Immutable configuration snapshot. Prefer `BoogieConfig.load()` over the constructor."""

    values: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | None = None) -> "BoogieConfig":
        """Read `boogie_sdk.yaml` (if present) then apply `BOOGIE_*` env var overrides."""
        values: dict[str, Any] = {}
        config_path = path or _DEFAULT_CONFIG_FILE
        if os.path.exists(config_path):
            values.update(cls._load_yaml(config_path))
        for key, value in os.environ.items():
            if key.startswith(_ENV_PREFIX):
                values[key[len(_ENV_PREFIX):].lower()] = value
        return cls(values=values)

    @staticmethod
    def _load_yaml(config_path: str) -> dict[str, Any]:
        try:
            import yaml
        except ImportError:
            return {}
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return dict(data)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def with_override(self, key: str, value: Any) -> "BoogieConfig":
        """Return a new BoogieConfig with one value overridden (config stays immutable)."""
        return BoogieConfig(values={**self.values, key: value})
