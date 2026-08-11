"""Tests for TmsgpackCustom: custom encode/decode for non-dataclass types."""

import struct
import textwrap
import pytest
from pathlib import Path

pytest.importorskip("semifun.di")
pytest.importorskip("semifun.plugins")

from tmsgpack.codec import NoDependencyInjector, TmsgpackCodec
from semifun.di.injector import DependencyInjector
from semifun.plugins.testing import create_registry_from_paths
from semifun.plugins.registry import _feature_map_from_registry


# --- Write test packages with custom codec types ---

def _write_custom_types_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "test_custom_types"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "types.py").write_text(textwrap.dedent("""\
        import struct
        from tmsgpack.codec_custom import TmsgpackCustom

        # --- Target types (not dataclasses) ---

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

        # --- Dict mode ---

        #::testing_custom_codec:Pair=CodecPairDict
        class CodecPairDict(TmsgpackCustom):
            def encode_dict(obj):
                return {'x': obj.x, 'y': obj.y}
            def decode_dict(*, x, y):
                return Pair(x=x, y=y)

        # --- List mode ---

        #::testing_custom_codec:Point=CodecPointList
        class CodecPointList(TmsgpackCustom):
            def encode_list(obj):
                return [obj.x, obj.y]
            def decode_list(x, y):
                return Point(x, y)
    """))
    (pkg / "types_bytes.py").write_text(textwrap.dedent("""\
        import struct
        from tmsgpack.codec_custom import TmsgpackCustom

        class FloatPair:
            def __init__(self, x, y):
                self.x = x
                self.y = y
            def __eq__(self, other):
                return (type(other) is FloatPair
                        and self.x == other.x and self.y == other.y)

        #::testing_custom_codec:FloatPair=CodecFloatPairBytes
        class CodecFloatPairBytes(TmsgpackCustom):
            def encode_bytes(obj):
                return struct.pack('<ff', obj.x, obj.y)
            def decode_bytes(data):
                x, y = struct.unpack('<ff', data)
                return FloatPair(x, y)
    """))
    return pkg


@pytest.fixture
def test_types(tmp_path):
    pkg = _write_custom_types_package(tmp_path)
    registry = create_registry_from_paths(
        packages=[("test_custom_types", pkg)],
    )
    feature_map = _feature_map_from_registry(registry, "testing_custom_codec")
    import test_custom_types.types as t
    import test_custom_types.types_bytes as tb
    return t, tb, feature_map


@pytest.fixture
def codec(test_types):
    t, tb, feature_map = test_types
    return TmsgpackCodec(sort_keys=False, di=NoDependencyInjector(),
                          plugin_feature_type=feature_map), t, tb


# --- Dict mode round-trip ---

def test_dict_mode_round_trip(codec):
    codec, t, tb = codec
    pair = t.Pair(x='hello', y=42)
    data = codec.encode(pair)
    restored = codec.decode(data)
    assert restored == pair


# --- List mode round-trip ---

def test_list_mode_round_trip(codec):
    codec, t, tb = codec
    point = t.Point(x=10, y=20)
    data = codec.encode(point)
    restored = codec.decode(data)
    assert restored == point


# --- Bytes mode round-trip ---

def test_bytes_mode_round_trip(codec):
    codec, t, tb = codec
    fp = tb.FloatPair(x=1.5, y=2.5)
    data = codec.encode(fp)
    restored = codec.decode(data)
    assert restored == fp


# --- Content hashing works with custom types ---

def test_content_hash_dict_mode(codec):
    codec, t, tb = codec
    codec_sorted = TmsgpackCodec(sort_keys=True, di=NoDependencyInjector(),
                                  plugin_feature_type=codec.plugin_feature_type)
    pair = t.Pair(x='a', y=1)
    h = codec_sorted.hash_to_str(pair)
    assert isinstance(h, str)
    assert len(h) == 22
    # Same value, same hash
    assert codec_sorted.hash_to_str(t.Pair(x='a', y=1)) == h


# --- Nested values in custom types ---

def test_dict_mode_nested_values(codec):
    codec, t, tb = codec
    pair = t.Pair(x=[1, 2, 3], y={'a': True})
    data = codec.encode(pair)
    restored = codec.decode(data)
    assert restored == pair


# --- Validation: mismatched modes ---

def test_mismatched_modes_raises():
    from tmsgpack.codec_custom import TmsgpackCustom
    with pytest.raises(TypeError, match="mode mismatch"):
        class Bad(TmsgpackCustom):
            def encode_dict(obj): return {}
            def decode_list(x): return None


def test_no_encode_raises():
    from tmsgpack.codec_custom import TmsgpackCustom
    with pytest.raises(TypeError, match="encode_dict, encode_list, encode_bytes"):
        class Bad(TmsgpackCustom):
            def decode_dict(*, x): return None


def test_no_decode_raises():
    from tmsgpack.codec_custom import TmsgpackCustom
    with pytest.raises(TypeError, match="decode_dict, decode_list, decode_bytes"):
        class Bad(TmsgpackCustom):
            def encode_dict(obj): return {}


# --- DI on decode ---

def _write_di_types_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "test_custom_di_types"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "types.py").write_text(textwrap.dedent("""\
        from tmsgpack.codec_custom import TmsgpackCustom
        from semifun.di.model import Inject

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

        #::testing_custom_di_codec:Widget=CodecWidget
        class CodecWidget(TmsgpackCustom):
            def encode_dict(obj, cache: Inject[Cache]):
                cache.put(obj.name, obj.data)
                return {'name': obj.name}
            def decode_dict(*, name, cache: Inject[Cache]):
                data = cache.get(name)
                return Widget(name=name, data=data)
    """))
    return pkg


def test_di_on_encode_and_decode(tmp_path):
    pkg = _write_di_types_package(tmp_path)
    registry = create_registry_from_paths(
        packages=[("test_custom_di_types", pkg)],
    )
    feature_map = _feature_map_from_registry(registry, "testing_custom_di_codec")
    import test_custom_di_types.types as t

    cache = t.Cache()
    injectors_map = lambda name, default=None: default
    di = DependencyInjector(injectors_map=injectors_map, seed_data={t.Cache: cache})
    codec = TmsgpackCodec(sort_keys=False, di=di, plugin_feature_type=feature_map)

    widget = t.Widget(name='gizmo', data=[1, 2, 3])
    data = codec.encode(widget)

    # The cache was populated during encode
    assert cache.store == {'gizmo': [1, 2, 3]}

    restored = codec.decode(data)
    assert restored == widget
