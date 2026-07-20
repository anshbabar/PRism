"""Unified-diff parser.

Parses ``git diff`` / unified-diff text into the models in ``models.py`` without
shelling out to git — the format is well specified, and a pure parser is
testable and dependency-free.

Handles: added / deleted / modified / renamed files, binary files, multi-hunk
files, add/delete counts, and changed line ranges. Robust to a missing trailing
newline marker (``\\ No newline at end of file``).
"""

from __future__ import annotations

import re

from app.diff.models import DiffFile, Hunk, LineRange, ParsedDiff

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")

# Path segments / suffixes that mark a file as a test.
_TEST_DIR_MARKERS = ("/tests/", "/test/", "__tests__/")
_TEST_SUFFIXES = ("_test.py", "_test.go", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")


def is_test_path(path: str) -> bool:
    """Heuristic: does this path look like a test file?"""
    p = path.lower()
    base = p.rsplit("/", 1)[-1]
    if p.startswith("tests/") or p.startswith("test/"):
        return True
    if any(marker in p for marker in _TEST_DIR_MARKERS):
        return True
    if base.startswith("test_"):
        return True
    return p.endswith(_TEST_SUFFIXES)


def _extension(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1].lower()


def _strip_prefix(path: str) -> str:
    """Drop a leading ``a/`` or ``b/`` git prefix."""
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


class _FileAcc:
    """Mutable accumulator for a single file block while parsing."""

    def __init__(self) -> None:
        self.old_path: str | None = None
        self.new_path: str | None = None
        self.status: str | None = None
        self.is_binary = False
        self.additions = 0
        self.deletions = 0
        self.hunks: list[Hunk] = []
        self.rename_from: str | None = None
        self.rename_to: str | None = None


def parse_diff(text: str) -> ParsedDiff:
    """Parse unified-diff ``text`` into a :class:`ParsedDiff`."""
    lines = text.splitlines()
    files: list[DiffFile] = []
    acc: _FileAcc | None = None

    # Hunk-in-progress state.
    cur_hunk: Hunk | None = None
    old_ln = 0
    new_ln = 0
    add_runs: list[tuple[int, int]] = []
    del_runs: list[tuple[int, int]] = []

    def close_hunk() -> None:
        nonlocal cur_hunk, add_runs, del_runs
        if cur_hunk is not None:
            cur_hunk.added_ranges = [LineRange(start=s, end=e, kind="added") for s, e in add_runs]
            cur_hunk.removed_ranges = [
                LineRange(start=s, end=e, kind="removed") for s, e in del_runs
            ]
        cur_hunk = None
        add_runs = []
        del_runs = []

    def close_file() -> None:
        nonlocal acc
        close_hunk()
        if acc is None:
            return
        path = acc.rename_to or acc.new_path or acc.old_path or ""
        old_path = None
        if acc.status == "renamed":
            path = acc.rename_to or acc.new_path or path
            old_path = acc.rename_from or acc.old_path
        status = acc.status or "modified"
        files.append(
            DiffFile(
                path=path,
                old_path=old_path,
                status=status,  # type: ignore[arg-type]
                additions=acc.additions,
                deletions=acc.deletions,
                extension=_extension(path),
                is_binary=acc.is_binary,
                is_test=is_test_path(path),
                hunks=acc.hunks,
            )
        )
        acc = None

    for line in lines:
        if line.startswith("diff --git "):
            close_file()
            acc = _FileAcc()
            # "diff --git a/<old> b/<new>"
            m = re.match(r"^diff --git (.+) (.+)$", line)
            if m:
                acc.old_path = _strip_prefix(m.group(1))
                acc.new_path = _strip_prefix(m.group(2))
            continue

        if acc is None:
            continue  # preamble before any file header

        if line.startswith("new file mode"):
            acc.status = "added"
        elif line.startswith("deleted file mode"):
            acc.status = "deleted"
        elif line.startswith("rename from "):
            acc.status = "renamed"
            acc.rename_from = line[len("rename from ") :].strip()
        elif line.startswith("rename to "):
            acc.status = "renamed"
            acc.rename_to = line[len("rename to ") :].strip()
        elif line.startswith("Binary files "):
            acc.is_binary = True
        elif line.startswith("--- "):
            target = line[4:].strip()
            if target == "/dev/null":
                acc.status = acc.status or "added"
            else:
                acc.old_path = _strip_prefix(target)
        elif line.startswith("+++ "):
            target = line[4:].strip()
            if target == "/dev/null":
                acc.status = "deleted"
            else:
                acc.new_path = _strip_prefix(target)
        elif line.startswith("@@"):
            close_hunk()
            m = _HUNK_RE.match(line)
            if not m:
                continue
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) is not None else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) is not None else 1
            cur_hunk = Hunk(
                old_start=old_start,
                old_lines=old_count,
                new_start=new_start,
                new_lines=new_count,
                header=m.group(5).strip(),
            )
            acc.hunks.append(cur_hunk)
            old_ln = old_start
            new_ln = new_start
        elif cur_hunk is not None:
            if line.startswith("\\"):
                continue  # "\ No newline at end of file"
            if line.startswith("+"):
                acc.additions += 1
                if add_runs and add_runs[-1][1] == new_ln - 1:
                    add_runs[-1] = (add_runs[-1][0], new_ln)
                else:
                    add_runs.append((new_ln, new_ln))
                new_ln += 1
            elif line.startswith("-"):
                acc.deletions += 1
                if del_runs and del_runs[-1][1] == old_ln - 1:
                    del_runs[-1] = (del_runs[-1][0], old_ln)
                else:
                    del_runs.append((old_ln, old_ln))
                old_ln += 1
            else:  # context line (starts with space, or blank)
                old_ln += 1
                new_ln += 1

    close_file()

    return ParsedDiff(
        files=files,
        files_changed=len(files),
        total_additions=sum(f.additions for f in files),
        total_deletions=sum(f.deletions for f in files),
    )
