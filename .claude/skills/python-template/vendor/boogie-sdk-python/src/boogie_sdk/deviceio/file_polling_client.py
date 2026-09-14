"""FilePollingClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.3 (deviceio).

Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable


class FilePollingClient:
    def watch(
        self, directory: Path, pattern: str, handler: Callable[[Path], None]
    ) -> None:
        for path in self.poll_once(directory, pattern):
            handler(path)

    def poll_once(self, directory: Path, pattern: str) -> list[Path]:
        return list(Path(directory).glob(pattern))
