from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import stat
from typing import BinaryIO, Iterator


@contextmanager
def open_binary_nofollow(path: Path) -> Iterator[BinaryIO]:
    expected = os.lstat(path)
    if stat.S_ISLNK(expected.st_mode):
        raise OSError(f"symlink file is not allowed: {path}")
    if not stat.S_ISREG(expected.st_mode):
        raise OSError(f"expected a regular file: {path}")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _file_identity(expected) != _file_identity(opened):
            raise OSError(f"file changed before it could be opened safely: {path}")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            yield handle
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _file_identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino
