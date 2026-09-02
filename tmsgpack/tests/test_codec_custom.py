"""Tests for TmsgpackCustom: custom encode/decode for non-dataclass types."""

import struct
import pytest
from dataclasses import dataclass

from tmsgpack.codec import NoDependencyInjector, TmsgpackCodec
from tmsgpack.codec_custom import TmsgpackCustom
from semifun.dispatch.Inject import Inject, injected_type
from semifun.dispatch.SemifunApp import SemifunApp
from semifun.dispatch.load_lookup_tables import LoadedFn


# --- Inline test types ---

class Pair:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __eq__(self, other):
        return type(other) is Pair and self.x == other.x and self.y == other.y

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __eq__(self, other):
        return type(other) is Point and self.x == other.x and self.y == other.y

class FloatPair:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __eq__(self, other):
        return (type(other) is FloatPair
                and self.x == other.x and self.y == other.y)


# --- Custom codecs ---

class CodecPairDict(TmsgpackCustom):
    def encode_dict(obj):
        return {'x': obj.x, 'y': obj.y}
    def decode_dict(*, x, y):
        return Pair(x=x, y=y)

class CodecPointList(TmsgpackCustom):
    def encode_list(obj):
        return [obj.x, obj.y]
    def decode_list(x, y):
        return Point(x, y)

class CodecFloatPairBytes(TmsgpackCustom):
    def encode_bytes(obj):
        return struct.pack('<ff', obj.x, obj.y)
    def decode_bytes(data):
        x, y = struct.unpack('<ff', data)
        return FloatPair(x, y)


# --- DI adapter for tests ---

@dataclass(frozen=True)
class _TestDiAdapter:
    lookup_table: dict
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
    'Pair': CodecPairDict,
    'Point': CodecPointList,
    'FloatPair': CodecFloatPairBytes,
}


@pytest.fixture
def codec():
    di = _TestDiAdapter(lookup_table=LOOKUP_TABLE, seed_data={})
    return TmsgpackCodec(sort_keys=False, di=di)


# --- Dict mode round-trip ---

def test_dict_mode_round_trip(codec):
    pair = Pair(x='hello', y=42)
    data = codec.encode(pair)
    restored = codec.decode(data)
    assert restored == pair


# --- List mode round-trip ---

def test_list_mode_round_trip(codec):
    point = Point(x=10, y=20)
    data = codec.encode(point)
    restored = codec.decode(data)
    assert restored == point


# --- Bytes mode round-trip ---

def test_bytes_mode_round_trip(codec):
    fp = FloatPair(x=1.5, y=2.5)
    data = codec.encode(fp)
    restored = codec.decode(data)
    assert restored == fp


# --- Content hashing works with custom types ---

def test_content_hash_dict_mode(codec):
    di = _TestDiAdapter(lookup_table=LOOKUP_TABLE, seed_data={})
    codec_sorted = TmsgpackCodec(sort_keys=True, di=di)
    pair = Pair(x='a', y=1)
    h = codec_sorted.hash_to_str(pair)
    assert isinstance(h, str)
    assert len(h) == 22
    # Same value, same hash
    assert codec_sorted.hash_to_str(Pair(x='a', y=1)) == h


# --- Nested values in custom types ---

def test_dict_mode_nested_values(codec):
    pair = Pair(x=[1, 2, 3], y={'a': True})
    data = codec.encode(pair)
    restored = codec.decode(data)
    assert restored == pair


# --- Validation: mismatched modes ---

def test_mismatched_modes_raises():
    with pytest.raises(TypeError, match="mode mismatch"):
        class Bad(TmsgpackCustom):
            def encode_dict(obj): return {}
            def decode_list(x): return None


def test_no_encode_raises():
    with pytest.raises(TypeError, match="encode_dict, encode_list, encode_bytes"):
        class Bad(TmsgpackCustom):
            def decode_dict(*, x): return None


def test_no_decode_raises():
    with pytest.raises(TypeError, match="decode_dict, decode_list, decode_bytes"):
        class Bad(TmsgpackCustom):
            def encode_dict(obj): return {}


# --- DI on encode and decode ---

class Cache:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store[key]
    def put(self, key, value):
        self.store[key] = value

class Widget:
    def __init__(self, name, data):
        self.name = name
        self.data = data
    def __eq__(self, other):
        return (type(other) is Widget
                and self.name == other.name
                and self.data == other.data)

class CodecWidget(TmsgpackCustom):
    def encode_dict(obj, cache: Inject[Cache]):
        cache.put(obj.name, obj.data)
        return {'name': obj.name}
    def decode_dict(*, name, cache: Inject[Cache]):
        data = cache.get(name)
        return Widget(name=name, data=data)


def test_di_on_encode_and_decode():
    cache = Cache()
    di = _TestDiAdapter(
        lookup_table={'Widget': CodecWidget},
        seed_data={Cache: cache},
    )
    codec = TmsgpackCodec(sort_keys=False, di=di)

    widget = Widget(name='gizmo', data=[1, 2, 3])
    data = codec.encode(widget)

    # The cache was populated during encode
    assert cache.store == {'gizmo': [1, 2, 3]}

    restored = codec.decode(data)
    assert restored == widget
