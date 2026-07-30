"""Tests for the all-knowable-data model and its cached properties.

These tests demonstrate:
- How FeatureMatch.loaded_object imports and returns the actual Python object
- How FeatureMatches.single resolves a unique match
- How specificity rules resolve Name=Alias overrides
- How FeaturePluginsIndex.find_features filters by any combination of criteria
- How verify_no_clashes detects ambiguous declarations
"""

import pytest
from pathlib import Path

from yb_tools.plugins.model import (
    FeatureSpec, IndexedFile,
    FeatureMatch, FeatureMatches, FeaturePluginsIndex,
)


# --- Helpers to build test data ---

def make_indexed_file(package, file_path, dotted_module_name, feature_specs):
    return IndexedFile(
        file_path=file_path or Path('/dev/null'),
        feature_package=package,
        dotted_module_name=dotted_module_name,
        # No test varies these, so they are stated here rather than added as
        # builder parameters every call site would have to repeat.
        entry_point_group=None,
        entry_point_name=None,
        feature_specs=feature_specs,
    )

def make_feature_spec(ftype, name, alias):
    return FeatureSpec(feature_type=ftype, feature_name=name, feature_alias=alias)

def make_match(package, ftype, name, alias, file_path, dotted_module_name):
    feature_spec = make_feature_spec(ftype, name, alias)
    return FeatureMatch(
        indexed_file=make_indexed_file(package, file_path, dotted_module_name, (feature_spec,)),
        feature_spec=feature_spec,
    )


# Every builder argument is required: each call
# below states the whole fixture, so what a test varies is visible in it.


# --- FeatureMatch.loaded_object ---

def test_loaded_object_imports_function():
    """loaded_object imports the module by dotted name and returns the named attribute."""
    from yb_tools.plugins.scanner import scan_file
    match = make_match(
        package='test_pkg', ftype='cli', name='scan_file',
        alias=None, file_path=None, dotted_module_name='yb_tools.plugins.scanner',
    )
    assert match.loaded_object is scan_file


def test_loaded_object_uses_alias():
    """When feature_alias is set, loaded_object resolves the aliased Python name."""
    from yb_tools.plugins.scanner import scan_file
    match = make_match(
        package='test_pkg', ftype='cli', name='extract',
        alias='scan_file', file_path=None, dotted_module_name='yb_tools.plugins.scanner',
    )
    assert match.loaded_object is scan_file


# --- FeatureMatches.single ---

def test_single_returns_unique_match():
    """single returns the one match when exactly one exists."""
    m = make_match(
        package='test_pkg', ftype='cli', name='greet',
        alias=None, file_path=None, dotted_module_name='test_pkg.module',
    )
    matches = FeatureMatches(matches=(m,))
    assert matches.single is m


def test_single_raises_on_no_match():
    matches = FeatureMatches(matches=())
    with pytest.raises(LookupError, match="No matching feature"):
        matches.single


def test_single_raises_on_ambiguous_implicit():
    """Two implicit (no alias) matches for the same name → error."""
    m1 = make_match(
        package='pkg_a', ftype='cli', name='greet',
        alias=None, file_path=None, dotted_module_name='test_pkg.module',
    )
    m2 = make_match(
        package='pkg_b', ftype='cli', name='greet',
        alias=None, file_path=None, dotted_module_name='test_pkg.module',
    )
    matches = FeatureMatches(matches=(m1, m2))
    with pytest.raises(LookupError, match="Ambiguous"):
        matches.single


def test_single_specificity_explicit_wins():
    """Explicit Name=Alias overrides an implicit bare Name."""
    implicit = make_match(
        package='base', ftype='cli', name='greet',
        alias=None, file_path=None, dotted_module_name='test_pkg.module',
    )
    explicit = make_match(
        package='extension', ftype='cli', name='greet',
        alias='SpecialGreet', file_path=None, dotted_module_name='test_pkg.module',
    )
    matches = FeatureMatches(matches=(implicit, explicit))
    assert matches.single is explicit


def test_single_raises_on_dual_explicit():
    """Two explicit overrides for the same name → error."""
    e1 = make_match(
        package='pkg_a', ftype='cli', name='greet',
        alias='Impl_A', file_path=None, dotted_module_name='test_pkg.module',
    )
    e2 = make_match(
        package='pkg_b', ftype='cli', name='greet',
        alias='Impl_B', file_path=None, dotted_module_name='test_pkg.module',
    )
    matches = FeatureMatches(matches=(e1, e2))
    with pytest.raises(LookupError, match="multiple explicit"):
        matches.single


# --- FeatureMatches.by_name ---

def test_by_name_indexes_matches():
    """by_name creates a dict from feature_name to FeatureMatch."""
    m1 = make_match(
        package='test_pkg', ftype='cli', name='greet',
        alias=None, file_path=None, dotted_module_name='test_pkg.module',
    )
    m2 = make_match(
        package='test_pkg', ftype='cli', name='add',
        alias=None, file_path=None, dotted_module_name='test_pkg.module',
    )
    matches = FeatureMatches(matches=(m1, m2))
    assert set(matches.by_name.keys()) == {'greet', 'add'}
    assert matches.by_name['greet'] is m1


def test_by_name_specificity_on_clash():
    """by_name applies specificity when two matches share a name."""
    implicit = make_match(
        package='base', ftype='cli', name='greet',
        alias=None, file_path=None, dotted_module_name='test_pkg.module',
    )
    explicit = make_match(
        package='ext', ftype='cli', name='greet',
        alias='ExtGreet', file_path=None, dotted_module_name='test_pkg.module',
    )
    matches = FeatureMatches(matches=(implicit, explicit))
    assert matches.by_name['greet'] is explicit


# --- FeaturePluginsIndex.find_features ---

def test_find_features_no_filter():
    """Every declaration in every indexed file, with all filters set to None."""
    idx = FeaturePluginsIndex(indexed_files=(
        make_indexed_file(
            package='test_pkg', file_path=Path('/f.py'),
            dotted_module_name='test_pkg.module',
            feature_specs=(
                make_feature_spec(ftype='cli', name='greet', alias=None),
                make_feature_spec(ftype='cli', name='add', alias=None),
            ),
        ),
    ))
    result = idx.find_features(feature_type=None, feature_name=None, feature_package=None)
    assert len(result.matches) == 2


def test_find_features_by_type():
    """Filter by feature_type returns only matching features."""
    idx = _make_mixed_index()
    cli_matches = idx.find_features(feature_type='cli', feature_name=None, feature_package=None)
    dc_matches = idx.find_features(feature_type='dataclass', feature_name=None, feature_package=None)
    assert all(m.feature_spec.feature_type == 'cli' for m in cli_matches.matches)
    assert all(m.feature_spec.feature_type == 'dataclass' for m in dc_matches.matches)


def test_find_features_by_name():
    idx = _make_mixed_index()
    result = idx.find_features(feature_type=None, feature_name='greet', feature_package=None)
    assert len(result.matches) == 1
    assert result.single.feature_spec.feature_name == 'greet'


def test_find_features_by_package():
    idx = _make_mixed_index()
    result = idx.find_features(feature_type=None, feature_name=None, feature_package='my_pkg')
    assert all(m.indexed_file.feature_package == 'my_pkg' for m in result.matches)


# --- verify_no_clashes ---

def test_verify_no_clashes_clean():
    idx = _make_mixed_index()
    assert idx.verify_no_clashes is True


def test_verify_no_clashes_detects_duplicate():
    """Two bare declarations of the same (type, name, package) → error."""
    fs = make_feature_spec(ftype='cli', name='greet', alias=None)
    idx = FeaturePluginsIndex(indexed_files=(
        make_indexed_file(package='test_pkg', file_path=Path('/a.py'),
                          dotted_module_name='test_pkg.module', feature_specs=(fs,)),
        make_indexed_file(package='test_pkg', file_path=Path('/b.py'),
                          dotted_module_name='test_pkg.module', feature_specs=(fs,)),
    ))
    with pytest.raises(LookupError, match="Clash"):
        idx.verify_no_clashes


# --- Test helpers ---

def _make_mixed_index():
    """An index with CLI and dataclass features for testing filters."""
    return FeaturePluginsIndex(indexed_files=(
        make_indexed_file(
            package='my_pkg', file_path=Path('/commands.py'),
            dotted_module_name='test_pkg.module',
            feature_specs=(make_feature_spec(ftype='cli', name='greet', alias=None),),
        ),
        make_indexed_file(
            package='my_pkg', file_path=Path('/models.py'),
            dotted_module_name='test_pkg.module',
            feature_specs=(make_feature_spec(ftype='dataclass', name='Point', alias=None),),
        ),
    ))
