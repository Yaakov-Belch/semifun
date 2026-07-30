"""Integration tests for TmsgpackCodec with DI and the feature registry."""

import textwrap
import pytest
from pathlib import Path

pytest.importorskip("yb_tools.di")
pytest.importorskip("yb_tools.plugins")

from tmsgpack.codec import NoDependencyInjector, TmsgpackCodec
from yb_tools.di.injector import DependencyInjector
from yb_tools.plugins.testing import create_registry_from_paths
from yb_tools.plugins.registry import (
    _feature_map_from_registry,
)


# --- Write a test package with annotated types ---

def _write_test_types_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "test_codec_types"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "types.py").write_text(textwrap.dedent("""\
        import enum
        from dataclasses import dataclass
        from yb_tools.di.model import Inject

        _HTTP_STATUS = (200, 404, 403, 401, 500)

        #::testing_tmsgpack_codec:FailureSeverity
        class FailureSeverity(enum.IntEnum):
            OK = 0
            PROBLEM = 1
            NOT_AUTHORIZED = 2
            NOT_AUTHENTICATED = 3
            UNEXPECTED = 4

            @property
            def http_status_code(self) -> int:
                return _HTTP_STATUS[self]

            def __str__(self):
                return self.name

        #::testing_tmsgpack_codec:Foo
        @dataclass(frozen=True)
        class Foo:
            x: str
            y: int

        @dataclass(frozen=True)
        class Dbh:
            pass

        #::testing_tmsgpack_codec:Bar
        @dataclass(frozen=True)
        class Bar:
            dbh: Inject[Dbh]
            x: str
    """))
    return pkg


@pytest.fixture
def test_types(tmp_path):
    pkg = _write_test_types_package(tmp_path)
    registry = create_registry_from_paths(
        packages=[("test_codec_types", pkg)],
    )
    feature_map = _feature_map_from_registry(registry, "testing_tmsgpack_codec")

    import test_codec_types.types as t
    return t, feature_map


def _make_injectors_map():
    _MISSING = object()
    # documented-default: mirrors FeatureMap.__call__ — omitting `default`
    # means "raise", which `None` cannot express.
    def lookup(name, default=_MISSING):   # documented-default
        if default is not _MISSING:
            return default
        raise LookupError(name)
    return lookup


@pytest.fixture
def codec(test_types):
    t, feature_map = test_types
    di = DependencyInjector(injectors_map=_make_injectors_map(), seed_data={t.Dbh: t.Dbh()})
    # testing-seam: pass feature_map callable instead of a string
    return TmsgpackCodec(sort_keys=False, di=di, plugin_feature_type=feature_map), t


@pytest.fixture
def codec_no_di(test_types):
    t, feature_map = test_types
    # testing-seam: pass feature_map callable instead of a string
    return TmsgpackCodec(sort_keys=False, di=NoDependencyInjector(),
                          plugin_feature_type=feature_map), t


# --- Round-trip: plain dataclass ---

def test_round_trip_dataclass(codec):
    codec, t = codec
    foo = t.Foo(x='hello', y=123)
    assert codec.decode(codec.encode(foo)) == foo


# --- Round-trip: enum ---

def test_round_trip_enum(codec):
    codec, t = codec
    for severity in t.FailureSeverity:
        assert codec.decode(codec.encode(severity)) == severity


# --- Round-trip: dataclass with Inject[T] fields ---

def test_round_trip_dataclass_with_inject(codec):
    codec, t = codec
    bar = t.Bar(dbh=t.Dbh(), x='world')
    data = codec.encode(bar)
    decoded = codec.decode(data)
    assert decoded.x == 'world'
    assert isinstance(decoded.dbh, t.Dbh)


# --- NoDependencyInjector: plain types work without DI ---

def test_no_di_dataclass(codec_no_di):
    codec, t = codec_no_di
    foo = t.Foo(x='abc', y=42)
    assert codec.decode(codec.encode(foo)) == foo


def test_no_di_enum(codec_no_di):
    codec, t = codec_no_di
    baz = t.FailureSeverity.PROBLEM
    assert codec.decode(codec.encode(baz)) == baz


# --- with_seed_data ---

def test_with_seed_data_round_trip(codec):
    codec, t = codec
    other_dbh = t.Dbh()
    codec2 = codec.with_seed_data({t.Dbh: other_dbh})
    bar = t.Bar(dbh=t.Dbh(), x='test')
    decoded = codec2.decode(codec2.encode(bar))
    assert decoded.x == 'test'
    assert decoded.dbh is other_dbh


# --- Encoder/decoder caches are shared after with_seed_data ---

def test_with_seed_data_shares_caches(codec):
    codec, t = codec
    codec2 = codec.with_seed_data({t.Dbh: t.Dbh()})
    assert codec2.encoder_cache is codec.encoder_cache
    assert codec2.decoder_cache is codec.decoder_cache


# --- Inject[T] without a DependencyInjector ---

def test_inject_field_without_an_injector_fails_on_encode():
    """`NoDependencyInjector` does not recognise Inject[T], so the field is serialized.

    Documented in [[tmsgpack:di-on-decode]]: exclusion depends on the
    injector, so without one the codec tries to encode the injected value and
    fails there — not on decode.
    """
    from dataclasses import dataclass

    from tmsgpack.codec import NoDependencyInjector, TmsgpackCodec
    from yb_tools.di.model import Inject

    class DbHandle:
        pass

    @dataclass(frozen=True)
    class NeedsInjection:
        dbh: Inject[DbHandle]
        x: str

    def feature_map(feature, default=None):
        return {'NeedsInjection': NeedsInjection}.get(feature, default)

    codec = TmsgpackCodec(
        sort_keys=True,
        di=NoDependencyInjector(),
        plugin_feature_type=feature_map,
    )
    with pytest.raises(ValueError, match='Cannot encode this type'):
        codec.encode(NeedsInjection(dbh=DbHandle(), x='hi'))
