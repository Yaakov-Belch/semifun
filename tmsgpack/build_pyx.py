"""Generate `tmsgpack/core.pyx` by concatenating `tmsgpack/src-parts/*`.

The Cython source is assembled from numbered fragments so that each part can
be edited on its own.  `core.pyx` is the generated result — never edit it.

`setup.py` calls `write_pyx()` before cythonizing, so a build always compiles
the current fragments.  The generated file is committed as well, because
`MANIFEST.in` ships `*.pyx` but not `src-parts/`: an sdist therefore contains
the assembled source and can be built without regenerating it.

`tests/test_build_pyx.py` asserts that the committed file matches what
`render_pyx()` produces, so the two cannot drift.

Run directly to regenerate by hand:

    uv run python build_pyx.py
"""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent
REPO_ROOT = PACKAGE_ROOT.parent
SRC_PARTS = PACKAGE_ROOT / 'tmsgpack' / 'src-parts'
PYX_PATH = PACKAGE_ROOT / 'tmsgpack' / 'core.pyx'
VERSION_FILE = REPO_ROOT / 'VERSION'

HEADER = """\
# THIS FILE IS AUTOMATICALLY CREATED BY build_pyx.py
# DON'T EDIT THIS FILE.  EDIT THE SOURCES, INSTEAD: tmsgpack/src-parts/*

__version__ = "{version}"

"""


def read_version() -> str:
    """The single source of truth for the version: repo-root VERSION file."""
    return VERSION_FILE.read_text().strip()


def render_pyx() -> str:
    """Return the full text of `core.pyx` without writing anything."""
    parts = sorted(SRC_PARTS.iterdir())
    if not parts:
        raise FileNotFoundError(f'No source fragments in {SRC_PARTS}')
    return HEADER.format(version=read_version()) + ''.join(
        p.read_text() for p in parts
    )


def write_pyx(path: Path) -> bool:
    """Write the rendered source to `path` if it differs.  True when rewritten.

    Writing only on change keeps the file's mtime stable, so an unchanged
    build does not make Cython recompile.  The destination is an argument so
    that tests can exercise this without touching the source tree.
    """
    new = render_pyx()
    if path.exists() and path.read_text() == new:
        return False
    path.write_text(new)
    return True


if __name__ == '__main__':
    changed = write_pyx(PYX_PATH)
    print(f'{PYX_PATH}: {"regenerated" if changed else "already current"}')
