"""Storage interfaces used by application services."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Repository(Protocol):
    def exists(self, relative_path: str) -> bool: ...

    def read_text(self, relative_path: str) -> str: ...

    def read_bytes(self, relative_path: str) -> bytes: ...

    def write_text(self, relative_path: str, content: str) -> None: ...

    def list_files(self, relative_path: str) -> list[str]: ...


class FilesystemRepository:
    """Filesystem-backed repository with root containment checks."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("repository path escapes configured root")
        return candidate

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).exists()

    def read_text(self, relative_path: str) -> str:
        return self._resolve(relative_path).read_text(encoding="utf-8")

    def read_bytes(self, relative_path: str) -> bytes:
        return self._resolve(relative_path).read_bytes()

    def write_text(self, relative_path: str, content: str) -> None:
        target = self._resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def list_files(self, relative_path: str) -> list[str]:
        target = self._resolve(relative_path)
        if not target.exists():
            return []
        if target.is_file():
            return [target.relative_to(self.root).as_posix()]
        return sorted(
            item.relative_to(self.root).as_posix()
            for item in target.rglob("*")
            if item.is_file()
        )
