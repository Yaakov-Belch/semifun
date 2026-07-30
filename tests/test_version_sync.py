"""All version sources in the repo must agree."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _read_toml_version(path: Path) -> str:
    text = path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, f"No version found in {path}"
    return match.group(1)


def test_all_versions_match():
    version_file = REPO_ROOT / "VERSION"
    root_toml = REPO_ROOT / "pyproject.toml"
    tmsgpack_toml = REPO_ROOT / "tmsgpack" / "pyproject.toml"
    package_json = REPO_ROOT / "tmsgpack-js" / "package.json"

    versions = {
        "VERSION": version_file.read_text().strip(),
        "pyproject.toml (yb-tools)": _read_toml_version(root_toml),
        "tmsgpack/pyproject.toml": _read_toml_version(tmsgpack_toml),
        "tmsgpack-js/package.json": json.loads(package_json.read_text())["version"],
    }

    unique = set(versions.values())
    assert len(unique) == 1, (
        "Version mismatch across sources:\n"
        + "\n".join(f"  {source}: {ver}" for source, ver in versions.items())
    )
