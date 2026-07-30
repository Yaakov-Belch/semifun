"""End-to-end tests for the sync DI API.

The sync API mirrors the async API; this file mirrors test_injector.py for
the cases that apply (sync injectors only). Async-specific cases (async
injectors, async generator cleanup) are tested separately as errors.
"""

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


class ReqCtx:
    pass


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


# --- All-injected (using Inject[T]) ---

def test_sync_all_injected_simple():
    def get_config():
        return Config(name="test")

    def feature(*, config: Inject[Config]):
        return config.name

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    assert di.sync_call_with_args(fn=feature, args=(), kwargs={}) == "test"


def test_sync_all_injected_chained():
    def get_config():
        return Config(name="db_config")

    def get_database(*, config: Inject[Config]):
        return Database(config)

    def feature(*, database: Inject[Database]):
        return database.config.name

    di = DependencyInjector(injectors_map=make_map({
        "Config": get_config,
        "Database": get_database,
    }), seed_data={})
    assert di.sync_call_with_args(fn=feature, args=(), kwargs={}) == "db_config"


def test_sync_all_injected_from_seed_data():
    def feature(*, config: Inject[Config]):
        return config.name

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    cfg = Config(name="from_root")
    assert di.with_seed_data({Config: cfg}).sync_call_with_args(fn=feature, args=(), kwargs={}) == "from_root"


def test_sync_all_injected_missing_type_raises():
    def feature(*, config: Inject[Config]):
        return config

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    with pytest.raises(LookupError, match="Config"):
        di.sync_call_with_args(fn=feature, args=(), kwargs={})


def test_sync_all_injected_circular_dependency_raises():
    def get_config(*, database: Inject[Database]):
        return Config(name="default")

    def get_database(*, config: Inject[Config]):
        return Database(config)

    def feature(*, config: Inject[Config]):
        return config

    di = DependencyInjector(injectors_map=make_map({
        "Config": get_config,
        "Database": get_database,
    }), seed_data={})
    with pytest.raises(RecursionError, match="Circular dependency"):
        di.sync_call_with_args(fn=feature, args=(), kwargs={})


def test_sync_all_injected_isinstance_check_failure():
    def get_config():
        return "not a Config"

    def feature(*, config: Inject[Config]):
        return config

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    with pytest.raises(TypeError, match="not an instance"):
        di.sync_call_with_args(fn=feature, args=(), kwargs={})


def test_sync_all_injected_caches_per_call():
    call_count = {"n": 0}

    def get_config():
        call_count["n"] += 1
        return Config(name="default")

    def get_database(*, config: Inject[Config]):
        return Database(config)

    def feature(*, config: Inject[Config], database: Inject[Database]):
        return (config, database, database.config)

    di = DependencyInjector(injectors_map=make_map({
        "Config": get_config,
        "Database": get_database,
    }), seed_data={})
    cfg, db, db_cfg = di.sync_call_with_args(fn=feature, args=(), kwargs={})
    assert cfg is db_cfg
    assert call_count["n"] == 1


# --- Generator-based cleanup ---

def test_sync_generator_cleanup():
    events: list[str] = []

    def get_config():
        events.append("config_setup")
        yield Config(name="from_gen")
        events.append("config_teardown")

    def feature(*, config: Inject[Config]):
        events.append("feature_running")
        return config.name

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    assert di.sync_call_with_args(fn=feature, args=(), kwargs={}) == "from_gen"
    assert events == ["config_setup", "feature_running", "config_teardown"]


def test_sync_cleanup_in_reverse_order():
    events: list[str] = []

    def get_config():
        events.append("config_setup")
        yield Config(name="default")
        events.append("config_teardown")

    def get_database(*, config: Inject[Config]):
        events.append("database_setup")
        yield Database(config)
        events.append("database_teardown")

    def feature(*, database: Inject[Database]):
        events.append("feature_running")
        return None

    di = DependencyInjector(injectors_map=make_map({
        "Config": get_config,
        "Database": get_database,
    }), seed_data={})
    di.sync_call_with_args(fn=feature, args=(), kwargs={})
    assert events == [
        "config_setup",
        "database_setup",
        "feature_running",
        "database_teardown",
        "config_teardown",
    ]


# --- Async-in-sync errors ---

def test_sync_rejects_async_injector():
    async def get_config():
        return Config(name="default")

    def feature(*, config: Inject[Config]):
        return config

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    with pytest.raises(TypeError, match="async \\(coroutine\\) injectors"):
        di.sync_call_with_args(fn=feature, args=(), kwargs={})


def test_sync_rejects_async_generator_injector():
    async def get_config():
        yield Config(name="default")

    def feature(*, config: Inject[Config]):
        return config

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    with pytest.raises(TypeError, match="async-generator injectors"):
        di.sync_call_with_args(fn=feature, args=(), kwargs={})


# --- call_with_args (mixed passthrough + inject) ---

def test_sync_call_with_args_passthrough_only():
    # test-fixture-data: a command whose default fills in for an unpassed arg.
    def feature(name, times=1):   # test-fixture-data
        return f"{name}*{times}"

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    assert di.sync_call_with_args(
        fn=feature, args=("Alice", 3), kwargs={}
    ) == "Alice*3"


def test_sync_call_with_args_with_inject():
    def get_ctx():
        return ReqCtx()

    def feature(name, *, ctx: Inject[ReqCtx]):
        return (name, ctx)

    di = DependencyInjector(injectors_map=make_map({"ReqCtx": get_ctx}), seed_data={})
    name, ctx = di.sync_call_with_args(
        fn=feature, args=("Alice",), kwargs={}
    )
    assert name == "Alice"
    assert isinstance(ctx, ReqCtx)


def test_sync_call_with_args_with_default_and_inject():
    def get_ctx():
        return ReqCtx()

    # test-fixture-data: proves a passthrough default survives injection --
    # the test asserts `times == 2` without passing it.
    def feature(name, times=2, *, ctx: Inject[ReqCtx]):   # test-fixture-data
        return (name, times, ctx)

    di = DependencyInjector(injectors_map=make_map({"ReqCtx": get_ctx}), seed_data={})
    name, times, ctx = di.sync_call_with_args(
        fn=feature, args=("Bob",), kwargs={}
    )
    assert name == "Bob"
    assert times == 2
    assert isinstance(ctx, ReqCtx)
