"""Tests for signature processing."""

import pytest

from semifun.di.model import Inject, MISSING
from semifun.di.signature_processing import (
    cache_key_for,
    process_call_with_args_signature,
)


# --- Sample dataclass-like types for the tests ---

class Config:
    pass


class Database:
    pass


class ReqCtx:
    pass


# A trivial injectors_map that uses a dict.
def make_map(d):
    _MISSING = object()

    # documented-default: mirrors FeatureMap.__call__ — omitting `default`
    # means "raise", which `None` cannot express.
    def lookup(name, default=_MISSING):   # documented-default
        if name in d:
            return d[name]
        if default is not _MISSING:
            return default
        raise LookupError(name)
    return lookup


def get_config():
    return Config()


def get_database(config: Config):
    return Database()


# --- call_with_args ---

def test_call_with_args_passthrough_only():
    # test-fixture-data: the SUT reads this default; the assertions below are on it.
    def fn(name, times=1): ...   # test-fixture-data
    sig = process_call_with_args_signature(fn, make_map({}))
    assert len(sig.injected_args) == 0
    assert len(sig.passthrough_args) == 2
    assert sig.passthrough_args[0].name == "name"
    assert sig.passthrough_args[0].default_value is MISSING
    assert sig.passthrough_args[1].name == "times"
    assert sig.passthrough_args[1].default_value == 1


def test_call_with_args_injected_only():
    def fn(*, ctx: Inject[ReqCtx]): ...
    sig = process_call_with_args_signature(fn, make_map({}))
    assert len(sig.injected_args) == 1
    assert len(sig.passthrough_args) == 0
    assert sig.injected_args[0].name == "ctx"
    assert sig.injected_args[0].type is ReqCtx


def test_call_with_args_mixed_with_keyword_only():
    # test-fixture-data: the SUT reads this default while also resolving Inject[T].
    def fn(name, times=1, *, ctx: Inject[ReqCtx]): ...   # test-fixture-data
    sig = process_call_with_args_signature(fn, make_map({}))
    assert len(sig.injected_args) == 1
    assert len(sig.passthrough_args) == 2
    assert sig.injected_args[0].name == "ctx"
    assert sig.passthrough_args[0].name == "name"
    assert sig.passthrough_args[1].name == "times"


def test_call_with_args_passthrough_with_type():
    def fn(name: str): ...
    sig = process_call_with_args_signature(fn, make_map({}))
    assert sig.passthrough_args[0].type is str
    assert sig.passthrough_args[0].name == "name"


def test_call_with_args_passthrough_no_annotation():
    def fn(name): ...
    sig = process_call_with_args_signature(fn, make_map({}))
    assert sig.passthrough_args[0].type is None


def test_call_with_args_all_inject_with_injector_lookup():
    def fn(*, config: Inject[Config], database: Inject[Database]): ...
    sig = process_call_with_args_signature(fn, make_map({
        "Config": get_config,
        "Database": get_database,
    }))
    assert len(sig.injected_args) == 2
    assert sig.injected_args[0].name == "config"
    assert sig.injected_args[0].injector_fn is get_config
    assert sig.injected_args[1].name == "database"
    assert sig.injected_args[1].injector_fn is get_database


def test_call_with_args_inject_no_injector_in_map():
    def fn(*, config: Inject[Config]): ...
    sig = process_call_with_args_signature(fn, make_map({}))
    assert sig.injected_args[0].injector_fn is None  # ok, may come from seed_data


# --- Cache key derivation ---

def test_cache_key_for_plain_function():
    def fn(): ...
    assert cache_key_for(fn) is fn


def test_cache_key_for_bound_method_uses_underlying_function():
    class Foo:
        def method(self, x: int): ...
    foo1 = Foo()
    foo2 = Foo()
    # Bound methods are distinct objects per access:
    assert foo1.method is not foo2.method
    # But the cache key (the underlying function) is the same:
    assert cache_key_for(foo1.method) is cache_key_for(foo2.method)
    assert cache_key_for(foo1.method) is Foo.method
