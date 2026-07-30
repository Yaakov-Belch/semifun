"""Bump the version across all packages, commit, tag, and push.

Usage:
    python bump_version_and_publish.py 0.2.23
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent

TARGETS = {
    "VERSION": REPO_ROOT / "VERSION",
    "pyproject.toml (semifun)": REPO_ROOT / "pyproject.toml",
    "tmsgpack/pyproject.toml": REPO_ROOT / "tmsgpack" / "pyproject.toml",
    "tmsgpack-js/package.json": REPO_ROOT / "tmsgpack-js" / "package.json",
}

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def update_version_file(path: Path, new: str) -> str:
    old = path.read_text().strip()
    path.write_text(new + "\n")
    return old


def update_toml_version(path: Path, new: str) -> str:
    text = path.read_text()
    match = re.search(r'^(version\s*=\s*)"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise ValueError(f"No version field found in {path}")
    old = match.group(2)
    updated = text[: match.start(2)] + new + text[match.end(2) :]
    path.write_text(updated)
    return old


def update_package_json(path: Path, new: str) -> str:
    data = json.loads(path.read_text())
    old = data["version"]
    data["version"] = new
    path.write_text(json.dumps(data, indent=2) + "\n")
    return old


def run(cmd):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=REPO_ROOT)
    if result.returncode != 0:
        print(f"Error: command failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <version>", file=sys.stderr)
        sys.exit(1)

    new_version = sys.argv[1]

    if not SEMVER_RE.match(new_version):
        print(f"Error: '{new_version}' is not a valid version (expected X.Y.Z)", file=sys.stderr)
        sys.exit(1)

    updaters = {
        "VERSION": update_version_file,
        "pyproject.toml (semifun)": update_toml_version,
        "tmsgpack/pyproject.toml": update_toml_version,
        "tmsgpack-js/package.json": update_package_json,
    }

    print("Updating versions:")
    for label, path in TARGETS.items():
        old = updaters[label](path, new_version)
        if old == new_version:
            print(f"  {label}: already {new_version}")
        else:
            print(f"  {label}: {old} -> {new_version}")

    print("\nCommit, tag, and push:")
    run(f'git commit -a -m "Bump version to {new_version}"')
    run(f"git tag v{new_version}")
    run("git push && git push --tags")

    print(f"\nDone. CI will publish v{new_version} to PyPI and npm.")


if __name__ == "__main__":
    main()
