"""Integration tests for TmsgpackCodec with DI and the dispatch system."""

import textwrap
import pytest
from pathlib import Path

from tmsgpack.codec import NoDependencyInjector, TmsgpackCodec
from semifun.dispatch.Inject import Inject, injected_type
from semifun.dispatch.SemifunApp import SemifunApp
from semifun.dispatch.load_lookup_tables import LoadedFn


# --- Inline test types (no file scanning needed) ---

import enum
from dataclasses import dataclass

#::testing_tmsgpack_codec:FailureSeverity
class FailureSeverity(enum.IntEnum):
    OK = 0
    PROBLEM = 1
    NOT_AUTHORIZED = 2
    NOT_AUTHENTICATED = 3
    UNEXPECTED = 4

@dataclass(frozen=True)
class Dbh:
    pass

#::testing_tmsgpack_codec:Foo
@dataclass(frozen=True)
class Foo:
    x: str
    y: int

#::testing_tmsgpack_codec:Bar
@dataclass(frozen=True)
class Bar:
    dbh: Inject[Dbh]
    x: str


# --- DI adapter for tests ---

@dataclass(frozen=True)
class _TestDiAdapter:
    """Test DI adapter satisfying DependencyInjectorProtocol."""
    lookup_table: dict   # {type_name: class}
    seed_data: dict

    @staticmethod
    def injected_type(annotation):
        return injected_type(annotation)

    def lookup_type(self, type_name):
        if type_name in self.lookup_table:
            return self.lookup_table[type_name]
        raise LookupError(f"No codec for {type_name}")

    def with_seed_data(self, seed_data):
        return _TestDiAdapter(lookup_table=self.lookup_table, seed_data={**self.seed_data, **seed_data})

    def sync_call_with_args(self, *, fn, args, kwargs):
        app = SemifunApp(entry_points_group={})
        with app.open_sync_scope(parent_scope=None, seed_data=self.seed_data, ftype='test') as scope:
            return scope.fn_call(fn=fn, args=args, kwargs=kwargs)


LOOKUP_TABLE = {
    'FailureSeverity': FailureSeverity,
    'Foo': Foo,
    'Bar': Bar,
}


@pytest.fixture
def codec():
    di = _TestDiAdapter(lookup_table=LOOKUP_TABLE, seed_data={Dbh: Dbh()})
    return TmsgpackCodec(sort_keys=False, di=di)


@pytest.fixture
def codec_no_di():
    return TmsgpackCodec(sort_keys=False, di=NoDependencyInjector())


# --- Round-trip: plain dataclass ---

def test_round_trip_dataclass(codec):
    foo = Foo(x='hello', y=123)
    assert codec.decode(codec.encode(foo)) == foo


# --- Round-trip: enum ---

def test_round_trip_enum(codec):
    for severity in FailureSeverity:
        assert codec.decode(codec.encode(severity)) == severity


# --- Round-trip: dataclass with Inject[T] fields ---

def test_round_trip_dataclass_with_inject(codec):
    bar = Bar(dbh=Dbh(), x='world')
    data = codec.encode(bar)
    decoded = codec.decode(data)
    assert decoded.x == 'world'
    assert isinstance(decoded.dbh, Dbh)


# --- NoDependencyInjector: plain types work without DI ---

def test_no_di_raises_on_lookup(codec_no_di):
    foo = Foo(x='abc', y=42)
    with pytest.raises(TypeError, match='Type lookup'):
        codec_no_di.encode(foo)


# --- with_seed_data ---

def test_with_seed_data_round_trip(codec):
    other_dbh = Dbh()
    codec2 = codec.with_seed_data({Dbh: other_dbh})
    bar = Bar(dbh=Dbh(), x='test')
    decoded = codec2.decode(codec2.encode(bar))
    assert decoded.x == 'test'
    assert decoded.dbh is other_dbh


# --- with_seed_data produces independent caches ---

def test_with_seed_data_has_independent_caches(codec):
    codec2 = codec.with_seed_data({Dbh: Dbh()})
    assert codec2.encoder_cache is not codec.encoder_cache
    assert codec2.decoder_cache is not codec.decoder_cache
