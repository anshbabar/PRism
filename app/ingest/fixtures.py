"""Local PR fixture ingestion.

Loads saved PR fixtures from ``eval/fixtures/sample_prs/<name>/`` — each with
``metadata.json``, ``diff.patch``, and ``expected.json``. This is the offline
demo/eval path: no GitHub App, no network.

Fixture names are validated and confined to the fixtures directory so an
attacker-supplied name can't traverse the filesystem.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

# repo_root/app/ingest/fixtures.py -> parents[2] == repo root
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "eval" / "fixtures" / "sample_prs"

_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class InvalidFixtureName(ValueError):
    """Raised when a fixture name fails validation."""


class FixtureNotFound(FileNotFoundError):
    """Raised when a validated fixture name has no matching directory."""


class Fixture(BaseModel):
    name: str
    metadata: dict[str, Any]
    diff_text: str
    expected: dict[str, Any]


def _validate_name(name: str) -> str:
    if not name or not _NAME_RE.match(name):
        raise InvalidFixtureName(
            f"Invalid fixture name {name!r}; allowed characters: letters, digits, '-', '_'."
        )
    return name


def list_fixtures() -> list[str]:
    """Return the available fixture names, sorted."""
    if not FIXTURES_DIR.is_dir():
        return []
    return sorted(p.name for p in FIXTURES_DIR.iterdir() if p.is_dir())


def load_fixture(name: str, *, root: Path | None = None) -> Fixture:
    """Load a fixture by name.

    Raises ``InvalidFixtureName`` for a malformed name and ``FixtureNotFound``
    if the directory or any required file is missing.
    """
    _validate_name(name)
    base = (root or FIXTURES_DIR).resolve()
    fixture_dir = (base / name).resolve()

    # Defense in depth: the resolved path must stay within the fixtures root.
    if not fixture_dir.is_relative_to(base):
        raise InvalidFixtureName(f"Fixture name escapes the fixtures directory: {name!r}")
    if not fixture_dir.is_dir():
        raise FixtureNotFound(f"No fixture named {name!r}")

    try:
        metadata = json.loads((fixture_dir / "metadata.json").read_text())
        diff_text = (fixture_dir / "diff.patch").read_text()
        expected = json.loads((fixture_dir / "expected.json").read_text())
    except FileNotFoundError as exc:
        raise FixtureNotFound(f"Fixture {name!r} is missing a required file: {exc}") from exc

    return Fixture(name=name, metadata=metadata, diff_text=diff_text, expected=expected)
