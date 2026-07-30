"""Round-trip tests: every value encodes and decodes back to an equal value.

Corpora are parametrised by *group*, not by value.  The generators below
produce several thousand values between them; one test item per value would be
slow to collect and would build test ids out of 2000-character strings.  One
item per group keeps the output readable and still names the failing value.
"""

import inspect
from dataclasses import dataclass, field
from functools import cached_property
from typing import Sequence

import pytest

from tmsgpack.api import EncodeDecode, basic_codec
from tmsgpack.core import TMsgpackError, __version__


# --- Value corpora ---

def _small_integers():
    return range(-2000, 2000)


def _integers():
    """Values either side of every power of two, both signs."""
    return [
        s * (2**e + d)
        for e in range(63)
        for d in range(-10, 10)
        for s in (-1, +1)
    ]


def _floats():
    return [3.1415926]


def _containers():
    """Strings, bytes and collections across a wide range of lengths."""
    return [
        v
        for e in range(18)
        for d in range(-2, 2)
        for f in (1, 1 / 3)
        for n in [int(f * 2**e + d)]
        for v in [
            "*" * n,
            b"*" * n,
            [12] * n,
            (12,) * n,
            {m: 3 * m + 1 for m in range(n)},
        ]
    ]


def _constants():
    return [True, False, None]


def _nested():
    return [[1, 2, 3, 4, {'a': 'hello', 'b': ['world', 5, 6, 7]}]]


def _large_integer():
    return [1760628047033313535]


BASIC_GROUPS = {
    'small integers': _small_integers,
    'integers': _integers,
    'float': _floats,
    'containers': _containers,
    'constants': _constants,
    'nested value': _nested,
    'large integer': _large_integer,
}


@pytest.mark.parametrize('group', sorted(BASIC_GROUPS))
def test_basic_codec_round_trip(group):
    """Every value in the group decodes back to an equal value."""
    for value in BASIC_GROUPS[group]():
        decoded = basic_codec.decode(basic_codec.encode(value))
        assert decoded == value, (
            f'{group}: a {type(value).__name__} did not round-trip'
            + (f' (length {len(value)})' if hasattr(value, '__len__') else '')
        )


# --- A codec that serializes registered dataclasses ---

@dataclass
class Foo:
    x: int
    y: int


@dataclass
class Unregistered:
    z: int


@dataclass
class MyCodec(EncodeDecode):
    """Minimal custom codec: serializes the dataclasses it is given."""
    sort_keys = True
    types: Sequence

    encode_cache: dict = field(default_factory=dict, init=False, repr=False)
    decode_cache: dict = field(default_factory=dict, init=False, repr=False)

    @cached_property
    def constructors(self):
        return {t.__name__: t for t in self.types}

    def prep_encode(self, value, target):
        return [None, self, value]

    def decode_codec(self, codec_type, source):
        if codec_type is None:
            return self
        raise TMsgpackError(f'Unsupported codec_type: {codec_type}')

    def encode_value(self, ectx):
        t = type(ectx.value)
        if t not in self.encode_cache:
            type_name = self.type_to_name(t)
            constructor = self.name_to_constructor(type_name)
            args = self.constructor_to_args(constructor)

            def encode_handler(ectx):
                value = ectx.value
                ectx.put_dict(type_name, {a: getattr(value, a) for a in args})

            self.encode_cache[t] = encode_handler
        self.encode_cache[t](ectx)

    def decode_from_bytes(self, dctx):
        raise TMsgpackError(f'No bytes extension defined: {dctx._type}')

    def decode_from_list(self, dctx):
        _type = dctx._type
        if _type not in self.decode_cache:
            constructor = self.name_to_constructor(_type)

            def decode_handler(dctx):
                return constructor(**dctx.take_dict())

            self.decode_cache[_type] = decode_handler
        return self.decode_cache[_type](dctx)

    def type_to_name(self, _type):
        return _type.__name__

    def name_to_constructor(self, name):
        if res := self.constructors.get(name, None):
            return res
        raise TMsgpackError(f'Unsupported type: {name}')

    def constructor_to_args(self, constructor):
        return inspect.signature(constructor).parameters.keys()


def test_custom_codec_round_trips_a_registered_dataclass():
    codec = MyCodec(types=[Foo])
    for value in [Foo(1, 2), Foo(2, 3)]:
        assert codec.decode(codec.encode(value)) == value


def test_custom_codec_rejects_an_unregistered_type():
    """An unregistered dataclass raises rather than encoding to something wrong."""
    codec = MyCodec(types=[Foo])
    with pytest.raises(TMsgpackError):
        codec.encode(Unregistered(z=1))


# --- Version ---

def test_version_matches_the_installed_metadata():
    """`__version__` is compiled into the extension; the metadata comes from pyproject.

    A mismatch means the extension in use was built from a different version
    than the installed package declares.  `test_build_pyx.py` checks the same
    version against the fragments the extension is generated from.
    """
    from importlib.metadata import version

    assert __version__ == version('tmsgpack')
