"""Zero-residue Temporary Directory and File Management."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List


class ManagedTempDir:
    """Creates a temporary working directory and guarantees cleanup on exit."""

    def __init__(self, prefix: str = "omni_media_"):
        self.prefix = prefix
        self.path: Path | None = None

    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(prefix=self.prefix))
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.path and self.path.exists():
            try:
                shutil.rmtree(self.path, ignore_errors=True)
            except Exception:
                pass


@contextmanager
def temp_cleanup(*file_paths: Path | str) -> Generator[None, None, None]:
    """Context manager ensuring specified files are removed when block finishes."""
    try:
        yield
    finally:
        for p in file_paths:
            if p:
                path = Path(p)
                if path.exists():
                    try:
                        if path.is_file():
                            path.unlink(missing_ok=True)
                        elif path.is_dir():
                            shutil.rmtree(path, ignore_errors=True)
                    except Exception:
                        pass
