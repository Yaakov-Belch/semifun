"""Tests for scanning #:: structured comments from Python source files.

These tests demonstrate:
- How #:: annotations are discovered in source files
- How the scanner ignores regular comments and code
- How annotations are parsed into (keyword, name, extra) triples
"""

from pathlib import Path
from semifun.plugins.scanner import scan_file, scan_package, parse_annotation


def test_scan_file_finds_annotations(tmp_path):
    """The scanner finds #:: lines and returns them as raw strings."""
    f = tmp_path / "example.py"
    f.write_text(
        "#::cli:greet\n"
        "def greet(name: str):\n"
        "    return f'Hello, {name}!'\n"
    )
    assert scan_file(f) == [
        "#::cli:greet",
    ]


def test_scan_file_ignores_regular_comments(tmp_path):
    """Only #:: comments are matched. Regular # comments are ignored."""
    f = tmp_path / "example.py"
    f.write_text(
        "# This is a regular comment\n"
        "#::cli:greet\n"
        "# Another comment\n"
        "#: sphinx docstring\n"
        "## markdown heading\n"
    )
    assert scan_file(f) == ["#::cli:greet"]


def test_scan_file_returns_empty_for_no_annotations(tmp_path):
    f = tmp_path / "plain.py"
    f.write_text("x = 1\n")
    assert scan_file(f) == []


def test_scan_package_collects_all_files(tmp_path):
    """scan_package walks subdirectories and returns relative paths."""
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "commands.py").write_text("#::cli:run\n")
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "models.py").write_text("#::dataclass:Point\n")
    (sub / "plain.py").write_text("x = 1\n")  # no annotations

    result = scan_package(pkg)

    assert "commands.py" in result
    assert "sub/models.py" in result
    assert "plain.py" not in result  # excluded: no annotations
    assert "__init__.py" not in result  # excluded: no annotations


# --- Annotation parsing ---

def test_parse_feature_type_basic():
    """#::cli:run → feature declaration, no alias."""
    assert parse_annotation("#::cli:run") == ("cli", "run", None)


def test_parse_feature_type_with_alias():
    """#::cli:run=run_server → feature name 'run', Python function 'run_server'."""
    assert parse_annotation("#::cli:run=run_server") == ("cli", "run", "run_server")


def test_parse_dataclass():
    assert parse_annotation("#::dataclass:UserProfile") == ("dataclass", "UserProfile", None)


def test_parse_dataclass_with_alias():
    """#::dataclass:CreateUser=ServerCreateUser → wire name vs Python class."""
    assert parse_annotation("#::dataclass:CreateUser=ServerCreateUser") == (
        "dataclass", "CreateUser", "ServerCreateUser"
    )


def test_no_keyword_is_reserved():
    """Any keyword names a feature type; none is special-cased in parsing."""
    assert parse_annotation("#::anything:x") == ("anything", "x", None)
    assert parse_annotation("#::whatever:x=y") == ("whatever", "x", "y")
    # A colon inside the value is part of the name, not a second field.
    assert parse_annotation("#::anything:a:b") == ("anything", "a:b", None)
