"""Data models for parsed diffs.

These are pure, JSON-serializable Pydantic models. The parser (``parser.py``)
produces a ``ParsedDiff``; the risk heuristics (``risk.py``) consume it. Keeping
the shape here lets the API layer and tests share one contract.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

FileStatus = Literal["added", "modified", "deleted", "renamed"]


class LineRange(BaseModel):
    """A contiguous run of changed lines within a hunk.

    ``kind="added"`` ranges use new-file line numbers; ``kind="removed"`` ranges
    use old-file line numbers.
    """

    start: int
    end: int
    kind: Literal["added", "removed"]


class Hunk(BaseModel):
    """A single ``@@ ... @@`` hunk."""

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    header: str  # context text after the second @@
    added_ranges: list[LineRange] = []
    removed_ranges: list[LineRange] = []


class DiffFile(BaseModel):
    """One file's worth of changes in a diff."""

    path: str
    old_path: str | None = None  # set for renames
    status: FileStatus
    additions: int = 0
    deletions: int = 0
    extension: str = ""  # lowercased, no dot; "" if none
    is_binary: bool = False
    is_test: bool = False
    hunks: list[Hunk] = []


class ParsedDiff(BaseModel):
    """The whole diff, parsed."""

    files: list[DiffFile] = []
    files_changed: int = 0
    total_additions: int = 0
    total_deletions: int = 0
