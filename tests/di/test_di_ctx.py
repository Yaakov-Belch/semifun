"""Tests for DependencyInjector — re-entrant DI access from inside feature functions."""

import pytest

from yb_tools.di.model import Inject
from yb_tools.di.injector import DependencyInjector


# --- Sample types ---

class Config:
    def __init__(self, name):
        self.name = name


class Database:
    def __init__(self, config: Config):
        self.config = config


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


# --- DependencyInjector is auto-seeded and injectable ---

async def test_di_available_via_call_with_args():
    """DependencyInjector is automatically available for injection."""
    def feature(*, di: Inject[DependencyInjector]):
        return di

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert isinstance(result, DependencyInjector)
    assert result is di


async def test_di_available_via_call_with_args_mixed():
    """DependencyInjector is available alongside passthrough args."""
    def feature(name, *, di: Inject[DependencyInjector]):
        return (name, di)

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    name, ctx = await di.async_call_with_args(
        fn=feature, args=("Alice",), kwargs={}
    )
    assert name == "Alice"
    assert isinstance(ctx, DependencyInjector)
    assert ctx is di


async def test_di_carries_seed_data():
    """DependencyInjector.seed_data reflects what was passed to with_seed_data."""
    cfg = Config(name="test")

    def feature(*, di: Inject[DependencyInjector]):
        return di.seed_data

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = await di.with_seed_data({Config: cfg}).async_call_with_args(fn=feature, args=(), kwargs={})
    assert result[Config] is cfg


# --- async re-entrant call_with_args ---

async def test_async_re_call_basic():
    """Re-entrant async_call_with_args calls a function through DI with the original seed_data."""
    cfg = Config(name="original")

    def get_config():
        return Config(name="from_injector")

    def inner(*, config: Inject[Config]):
        return config.name

    async def outer(*, di: Inject[DependencyInjector]):
        return await di.async_call_with_args(fn=inner, args=(), kwargs={})

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = await di.with_seed_data({Config: cfg}).async_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "original"


async def test_async_re_call_with_seed_data_override():
    """with_seed_data merges with and overrides the original seed_data."""
    cfg_original = Config(name="original")
    cfg_override = Config(name="override")

    def inner(*, config: Inject[Config]):
        return config.name

    async def outer(*, di: Inject[DependencyInjector]):
        return await di.with_seed_data({Config: cfg_override}).async_call_with_args(fn=inner, args=(), kwargs={})

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = await di.with_seed_data({Config: cfg_original}).async_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "override"


async def test_async_re_call_uses_injectors():
    """Re-invoked call resolves types via the injectors_map."""
    def get_config():
        return Config(name="injected")

    def inner(*, config: Inject[Config]):
        return config.name

    async def outer(*, di: Inject[DependencyInjector]):
        return await di.async_call_with_args(fn=inner, args=(), kwargs={})

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = await di.async_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "injected"


async def test_async_re_call_cleanup():
    """Generator cleanup runs in the re-invoked call."""
    events: list[str] = []

    def get_config():
        events.append("setup")
        yield Config(name="gen")
        events.append("teardown")

    def inner(*, config: Inject[Config]):
        events.append("inner")
        return config.name

    async def outer(*, di: Inject[DependencyInjector]):
        result = await di.async_call_with_args(fn=inner, args=(), kwargs={})
        events.append("after_re_call")
        return result

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = await di.async_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "gen"
    assert events == ["setup", "inner", "teardown", "after_re_call"]


# --- async re-entrant call_with_args (mixed passthrough) ---

async def test_async_recall_with_args_passthrough():
    """Re-entrant async_call_with_args with passthrough args."""
    cfg = Config(name="original")

    def inner(prefix: str, *, config: Inject[Config]):
        return f"{prefix}:{config.name}"

    async def outer(*, di: Inject[DependencyInjector]):
        return await di.async_call_with_args(fn=inner, args=("hello",), kwargs={})

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = await di.with_seed_data({Config: cfg}).async_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "hello:original"


async def test_async_recall_with_args_with_kwargs():
    """Re-entrant async_call_with_args passes kwargs."""
    cfg = Config(name="original")

    # test-fixture-data: a re-entrant call target whose default is exercised
    # when the outer call passes no `prefix`.
    def inner(prefix: str = "", *, config: Inject[Config]):   # test-fixture-data
        return f"{prefix}:{config.name}"

    async def outer(*, di: Inject[DependencyInjector]):
        return await di.async_call_with_args(fn=inner, args=(), kwargs={"prefix": "kw"})

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = await di.with_seed_data({Config: cfg}).async_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "kw:original"


async def test_async_recall_with_args_with_seed_data():
    """with_seed_data works with re-entrant async_call_with_args."""
    cfg_original = Config(name="original")
    cfg_override = Config(name="override")

    def inner(prefix: str, *, config: Inject[Config]):
        return f"{prefix}:{config.name}"

    async def outer(*, di: Inject[DependencyInjector]):
        return await di.with_seed_data({Config: cfg_override}).async_call_with_args(
            fn=inner, args=("hello",), kwargs={},
        )

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = await di.with_seed_data({Config: cfg_original}).async_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "hello:override"


# --- sync re-entrant call_with_args ---

def test_sync_re_call_basic():
    """Re-entrant sync_call_with_args calls a function through DI with the original seed_data."""
    cfg = Config(name="original")

    def inner(*, config: Inject[Config]):
        return config.name

    def outer(*, di: Inject[DependencyInjector]):
        return di.sync_call_with_args(fn=inner, args=(), kwargs={})

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = di.with_seed_data({Config: cfg}).sync_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "original"


def test_sync_re_call_with_seed_data_override():
    """with_seed_data merges with and overrides the original seed_data."""
    cfg_original = Config(name="original")
    cfg_override = Config(name="override")

    def inner(*, config: Inject[Config]):
        return config.name

    def outer(*, di: Inject[DependencyInjector]):
        return di.with_seed_data({Config: cfg_override}).sync_call_with_args(fn=inner, args=(), kwargs={})

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = di.with_seed_data({Config: cfg_original}).sync_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "override"


def test_sync_re_call_uses_injectors():
    """Re-invoked call resolves types via the injectors_map."""
    def get_config():
        return Config(name="injected")

    def inner(*, config: Inject[Config]):
        return config.name

    def outer(*, di: Inject[DependencyInjector]):
        return di.sync_call_with_args(fn=inner, args=(), kwargs={})

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = di.sync_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "injected"


def test_sync_re_call_cleanup():
    """Generator cleanup runs in the re-invoked call."""
    events: list[str] = []

    def get_config():
        events.append("setup")
        yield Config(name="gen")
        events.append("teardown")

    def inner(*, config: Inject[Config]):
        events.append("inner")
        return config.name

    def outer(*, di: Inject[DependencyInjector]):
        result = di.sync_call_with_args(fn=inner, args=(), kwargs={})
        events.append("after_re_call")
        return result

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = di.sync_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "gen"
    assert events == ["setup", "inner", "teardown", "after_re_call"]


# --- sync re-entrant with passthrough ---

def test_sync_recall_with_args_passthrough():
    """Re-entrant sync_call_with_args with passthrough args."""
    cfg = Config(name="original")

    def inner(prefix: str, *, config: Inject[Config]):
        return f"{prefix}:{config.name}"

    def outer(*, di: Inject[DependencyInjector]):
        return di.sync_call_with_args(fn=inner, args=("hello",), kwargs={})

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = di.with_seed_data({Config: cfg}).sync_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "hello:original"


def test_sync_recall_with_args_with_seed_data():
    """with_seed_data works with re-entrant sync_call_with_args."""
    cfg_original = Config(name="original")
    cfg_override = Config(name="override")

    def inner(prefix: str, *, config: Inject[Config]):
        return f"{prefix}:{config.name}"

    def outer(*, di: Inject[DependencyInjector]):
        return di.with_seed_data({Config: cfg_override}).sync_call_with_args(
            fn=inner, args=("hello",), kwargs={},
        )

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = di.with_seed_data({Config: cfg_original}).sync_call_with_args(fn=outer, args=(), kwargs={})
    assert result == "hello:override"


# --- Sync availability ---

def test_sync_di_available():
    """DependencyInjector is available in sync DI too."""
    def feature(*, di: Inject[DependencyInjector]):
        return di

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = di.sync_call_with_args(fn=feature, args=(), kwargs={})
    assert isinstance(result, DependencyInjector)
    assert result is di


def test_di_not_overridden_by_seed_data():
    """DependencyInjector in seed_data does not override the auto-seeded one."""
    fake_di = DependencyInjector(injectors_map=make_map({}), seed_data={})

    def feature(*, di: Inject[DependencyInjector]):
        return di

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = di.with_seed_data({DependencyInjector: fake_di}).sync_call_with_args(fn=feature, args=(), kwargs={})
    assert result is not fake_di
