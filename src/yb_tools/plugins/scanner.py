"""Scan Python source files for #:: structured comments."""

import re
from pathlib import Path

from .model import FeatureSpec, IndexedFile

ANNOTATION_RE = re.compile(r'^#::(\w+):(.+)$')


def scan_file(file_path: Path) -> list[str]:
    """Scan a Python file for #:: structured comments. Returns raw comment lines."""
    results = []
    for line in file_path.read_text().splitlines():
        stripped = line.strip()
        if ANNOTATION_RE.match(stripped):
            results.append(stripped)
    return results


def scan_package(package_path: Path) -> dict[str, list[str]]:
    """Scan all .py files in a package directory for #:: comments.

    Returns {relative_path: [comments]} for files with at least one comment.
    Files without structured comments are excluded.
    """
    result = {}
    for py_file in sorted(package_path.rglob('*.py')):
        comments = scan_file(py_file)
        if comments:
            rel = str(py_file.relative_to(package_path))
            result[rel] = comments
    return result


def parse_annotation(line: str) -> tuple[str, str, str | None]:
    """Parse a #:: line into (keyword, name, extra).

    #::dataclass:Foo              → ('dataclass', 'Foo', None)
    #::dataclass:Foo=Bar          → ('dataclass', 'Foo', 'Bar')
    #::cli:run=run_server         → ('cli', 'run', 'run_server')

    Every keyword names a feature type; none is reserved, and the value is
    taken literally apart from an `=alias` suffix.
    """
    m = ANNOTATION_RE.match(line)
    if m is None:
        raise ValueError(f"Not a valid #:: annotation: {line}")
    keyword = m.group(1)
    value = m.group(2)
    if '=' in value:
        name, alias = value.split('=', 1)
        return keyword, name, alias
    return keyword, value, None


def _dotted_module_name(package_name: str, relative_path: str) -> str:
    """Compose the dotted module name for a file inside an installed package.

    Examples:
        ('table_converter', 'formats/csv_format.py') → 'table_converter.formats.csv_format'
        ('table_converter', '__init__.py')            → 'table_converter'
        ('table_converter', 'formats/__init__.py')    → 'table_converter.formats'
    """
    parts = list(Path(relative_path).with_suffix('').parts)
    if parts and parts[-1] == '__init__':
        parts.pop()
    return '.'.join([package_name, *parts])


def build_indexed_file(
    package_path: Path,
    relative_path: str,
    comments: list[str],
    default_package: str,
    entry_point_group: str | None,
    entry_point_name: str | None,
) -> IndexedFile:
    """Parse one file's raw comments into an IndexedFile of FeatureSpec objects.

    `entry_point_group` / `entry_point_name` are `None` when the file was not
    reached through an entry point; pass them explicitly, per
    [[:no-default-values]].
    """
    feature_specs = []
    for comment in comments:
        keyword, name, extra = parse_annotation(comment)
        feature_specs.append(FeatureSpec(
            feature_type=keyword,
            feature_name=name,
            feature_alias=extra,
        ))
    return IndexedFile(
        file_path=package_path / relative_path,
        feature_package=default_package,
        dotted_module_name=_dotted_module_name(default_package, relative_path),
        entry_point_group=entry_point_group,
        entry_point_name=entry_point_name,
        feature_specs=tuple(feature_specs),
    )
