"""Tests for registry creation and index caching.

These tests demonstrate:
- Creating a registry from explicit paths (no installed packages needed)
- The create_disk_cache mechanism writes feature_plugins_index.json
- Reading back from cache produces the same registry
- The full flow: scan → index → registry → find_features → loaded_object
"""

import json
import pytest
from pathlib import Path

from yb_tools.plugins.testing import create_registry_from_paths
from yb_tools.plugins.model import FeaturePluginsIndex
from yb_tools.plugins.index import INDEX_FILENAME, get_index, write_index, build_index


def _write_sample_package(tmp_path):
    """Create a minimal package with CLI and dataclass features."""
    pkg = tmp_path / "sample_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "commands.py").write_text(
        "#::cli:greet\n"
        "def greet(name: str = 'world'):\n"
        "    '''Greet someone.'''\n"
        "    return f'Hello, {name}!'\n"
        "\n"
        "#::cli:add\n"
        "def add(a: int = 0, b: int = 0):\n"
        "    '''Add two numbers.'''\n"
        "    return a + b\n"
    )
    (pkg / "models.py").write_text(
        "#::dataclass:Point\n"
        "class Point:\n"
        "    def __init__(self, x=0, y=0):\n"
        "        self.x, self.y = x, y\n"
    )
    return pkg


# --- Index building and caching ---

def test_build_index_scans_package(tmp_path):
    """build_index returns a dict of relative paths to comment lists."""
    pkg = _write_sample_package(tmp_path)
    index = build_index(pkg)
    assert "commands.py" in index
    assert "#::cli:greet" in index["commands.py"]
    assert "models.py" in index
    assert "__init__.py" not in index


def test_write_and_read_index(tmp_path):
    """Writing then reading an index produces the same data."""
    pkg = _write_sample_package(tmp_path)
    original = build_index(pkg)
    write_index(pkg, original)
    assert (pkg / INDEX_FILENAME).exists()
    cached = get_index(pkg, create_disk_cache=False)  # reads from cache
    assert cached == original


def test_create_disk_cache_writes_and_overwrites(tmp_path):
    """create_disk_cache=True always scans and writes, even if a cache exists."""
    pkg = _write_sample_package(tmp_path)
    cache_file = pkg / INDEX_FILENAME
    cache_file.write_text('{"stale": []}')  # stale cache
    index = get_index(pkg, create_disk_cache=True)
    assert "commands.py" in index  # fresh scan, not stale
    fresh_on_disk = json.loads(cache_file.read_text())
    assert "commands.py" in fresh_on_disk


def test_get_index_prefers_cache(tmp_path):
    """With create_disk_cache=False, get_index reads the cache and does not scan."""
    pkg = _write_sample_package(tmp_path)
    fake_cache = {"fake.py": ["#::cli:fake"]}
    write_index(pkg, fake_cache)
    index = get_index(pkg, create_disk_cache=False)
    assert index == fake_cache  # used cache, didn't scan


# --- Full registry flow ---

def test_create_registry_from_paths(tmp_path):
    """Create a registry, find features, load objects."""
    pkg = _write_sample_package(tmp_path)
    registry = create_registry_from_paths(
        packages=[("sample_pkg", pkg)],
    )
    # Find CLI features
    cli = registry.find_features(feature_type='cli', feature_name=None, feature_package=None)
    assert len(cli.matches) == 2
    assert set(cli.by_name.keys()) == {'greet', 'add'}

    # Load and call a function
    greet_fn = cli.by_name['greet'].loaded_object
    assert greet_fn(name='Alice') == 'Hello, Alice!'


def test_registry_feature_package_default(tmp_path):
    """Without a package rename, feature_package is the actual package name."""
    pkg = _write_sample_package(tmp_path)
    registry = create_registry_from_paths(
        packages=[("sample_pkg", pkg)],
    )
    match = registry.find_features(feature_type='cli', feature_name='greet', feature_package=None).single
    assert match.indexed_file.feature_package == 'sample_pkg'


def test_cache_is_deterministic(tmp_path):
    """Building the index twice produces identical JSON (deterministic for git)."""
    pkg = _write_sample_package(tmp_path)
    index1 = build_index(pkg)
    index2 = build_index(pkg)
    json1 = json.dumps(index1, indent=2, sort_keys=True)
    json2 = json.dumps(index2, indent=2, sort_keys=True)
    assert json1 == json2


# --- yb_tools.plugins.testing: every declaration resolves ---

def test_load_all_features_imports_every_declaration(tmp_path):
    """load_all_features proves each #:: declaration names a real object."""
    from yb_tools.plugins.testing import get_feature_types, load_all_features

    pkg = tmp_path / "load_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "features.py").write_text(
        "#::cli:greet\n"
        "def greet(): return 'hi'\n"
        "\n"
        "#::reader:load\n"
        "def load(): return 'data'\n"
    )
    registry = create_registry_from_paths(
        packages=[("load_pkg", pkg)],
    )

    assert get_feature_types(registry) == ['cli', 'reader']

    features = load_all_features(registry, feature_types=None)
    assert [(f.feature_type, f.name) for f in features] == [('cli', 'greet'), ('reader', 'load')]
    assert all(callable(f.object) for f in features)

    only_cli = load_all_features(registry, feature_types=['cli'])
    assert [f.name for f in only_cli] == ['greet']


def test_load_all_features_raises_on_a_broken_declaration(tmp_path):
    """A #:: name that does not exist in the module is caught, not ignored."""
    from yb_tools.plugins.testing import load_all_features

    pkg = tmp_path / "broken_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "features.py").write_text(
        "#::cli:typo_in_the_comment\n"
        "def actual_name(): return 'hi'\n"
    )
    registry = create_registry_from_paths(
        packages=[("broken_pkg", pkg)],
    )
    with pytest.raises(AttributeError):
        load_all_features(registry, feature_types=None)
