"""ConfigClient: simulated remote config-center client with hot-reload callbacks.

See boogie-sdk-api.md (this skill's library doc) section 4 (共用慣例) and the infra overview
in section 1 ("遠端設定中心 client(hot reload)"). Real implementation is fake/local
only: `reload()` re-reads the same source `BoogieConfig.load()` would use.
"""

from __future__ import annotations

from typing import Any, Callable

from boogie_sdk.config.config import BoogieConfig


class ConfigClient:
    def __init__(self, config: BoogieConfig):
        self._config = config
        self._listeners: list[Callable[[BoogieConfig], None]] = []

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def reload(self, path: str | None = None) -> None:
        self._config = BoogieConfig.load(path)
        for listener in self._listeners:
            listener(self._config)

    def on_change(self, listener: Callable[[BoogieConfig], None]) -> None:
        self._listeners.append(listener)
