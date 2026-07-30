"""The generated Cython source must match its fragments and the declared version."""

import importlib.util
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parent.parent


def _load_build_pyx():
    """Import `build_pyx.py`, which sits beside setup.py rather than in the package."""
    spec = importlib.util.spec_from_file_location(
        'build_pyx', PACKAGE_ROOT / 'build_pyx.py',
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_pyx_matches_its_fragments():
    """`core.pyx` is generated; a stale committed copy is a silent trap.

    An sdist ships the assembled `.pyx` (MANIFEST.in), so a copy that no
    longer matches `src-parts/` would build something nobody wrote.
    """
    build_pyx = _load_build_pyx()
    assert build_pyx.PYX_PATH.read_text() == build_pyx.render_pyx(), (
        'tmsgpack/core.pyx is out of date with tmsgpack/src-parts/*. '
        'Regenerate it: uv run python build_pyx.py'
    )


def test_generated_version_matches_the_declared_version():
    """The version compiled into the extension comes from [project] version."""
    from tmsgpack.core import __version__

    build_pyx = _load_build_pyx()
    assert __version__ == build_pyx.read_version()


def test_render_is_deterministic_and_ordered():
    """Fragments concatenate in numeric-name order, so the output is stable."""
    build_pyx = _load_build_pyx()
    assert build_pyx.render_pyx() == build_pyx.render_pyx()

    names = [p.name for p in sorted(build_pyx.SRC_PARTS.iterdir())]
    assert names == sorted(names)
    assert names[0].startswith('01-')


def test_write_pyx_only_writes_when_the_content_differs(tmp_path):
    """Rewriting an unchanged file would churn its mtime and force a rebuild.

    Writes to a temporary path: a test must not modify the source tree.
    """
    build_pyx = _load_build_pyx()
    target = tmp_path / 'core.pyx'

    assert build_pyx.write_pyx(target) is True     # created
    assert build_pyx.write_pyx(target) is False    # unchanged, left alone

    target.write_text('stale')
    assert build_pyx.write_pyx(target) is True     # differs, rewritten
    assert target.read_text() == build_pyx.render_pyx()
