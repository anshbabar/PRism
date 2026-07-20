"""Tests for the unified-diff parser."""

from __future__ import annotations

from app.diff.parser import is_test_path, parse_diff

ADDED = """\
diff --git a/app/new_mod.py b/app/new_mod.py
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/app/new_mod.py
@@ -0,0 +1,2 @@
+def foo():
+    return 1
"""

DELETED = """\
diff --git a/app/old_mod.py b/app/old_mod.py
deleted file mode 100644
index abc1234..0000000
--- a/app/old_mod.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def bar():
-    return 2
"""

MODIFIED_MULTI_HUNK = """\
diff --git a/app/svc.py b/app/svc.py
index 1111111..2222222 100644
--- a/app/svc.py
+++ b/app/svc.py
@@ -1,3 +1,3 @@
 import os
-x = 1
+x = 2
@@ -10,2 +10,4 @@ def g():
     y = 3
+    z = 4
+    w = 5
"""

RENAMED = """\
diff --git a/old/name.py b/new/name.py
similarity index 100%
rename from old/name.py
rename to new/name.py
"""

BINARY = """\
diff --git a/img/logo.png b/img/logo.png
new file mode 100644
index 0000000..aaaaaaa
Binary files /dev/null and b/img/logo.png differ
"""


def test_added_file() -> None:
    diff = parse_diff(ADDED)
    assert diff.files_changed == 1
    f = diff.files[0]
    assert f.path == "app/new_mod.py"
    assert f.status == "added"
    assert f.additions == 2
    assert f.deletions == 0
    assert f.extension == "py"
    assert f.is_test is False
    assert f.is_binary is False


def test_deleted_file() -> None:
    f = parse_diff(DELETED).files[0]
    assert f.path == "app/old_mod.py"
    assert f.status == "deleted"
    assert f.deletions == 2
    assert f.additions == 0


def test_modified_multi_hunk_counts_and_ranges() -> None:
    f = parse_diff(MODIFIED_MULTI_HUNK).files[0]
    assert f.status == "modified"
    assert f.additions == 3
    assert f.deletions == 1
    assert len(f.hunks) == 2

    # First hunk: one line swapped at new-line 2 / old-line 2.
    h1 = f.hunks[0]
    assert h1.added_ranges[0].start == 2
    assert h1.added_ranges[0].end == 2
    assert h1.removed_ranges[0].start == 2

    # Second hunk: two lines added at new-lines 11-12.
    h2 = f.hunks[1]
    assert h2.added_ranges[0].start == 11
    assert h2.added_ranges[0].end == 12


def test_renamed_file() -> None:
    f = parse_diff(RENAMED).files[0]
    assert f.status == "renamed"
    assert f.path == "new/name.py"
    assert f.old_path == "old/name.py"


def test_binary_file() -> None:
    f = parse_diff(BINARY).files[0]
    assert f.is_binary is True
    assert f.extension == "png"


def test_totals_across_files() -> None:
    diff = parse_diff(ADDED + MODIFIED_MULTI_HUNK)
    assert diff.files_changed == 2
    assert diff.total_additions == 2 + 3
    assert diff.total_deletions == 0 + 1


def test_empty_diff() -> None:
    diff = parse_diff("")
    assert diff.files == []
    assert diff.files_changed == 0
    assert diff.total_additions == 0


def test_is_test_path() -> None:
    assert is_test_path("tests/test_x.py")
    assert is_test_path("app/foo_test.py")
    assert is_test_path("web/app/page.test.tsx")
    assert is_test_path("src/__tests__/a.spec.ts")
    assert not is_test_path("app/foo.py")
    assert not is_test_path("app/api/routes_orders.py")
