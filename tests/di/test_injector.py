"""End-to-end tests for the DependencyInjector."""

import pytest

from semifun.di.model import Inject
from semifun.di.injector import DependencyInjector


# --- Sample dataclass-like types ---

class Config:
    def __init__(self, name):
        self.name = name


class Database:
    def __init__(self, config: Config):
        self.config = config


class ReqCtx:
    pass


# --- A trivial injectors_map (callable that mimics get_cached_feature_map's lookup) ---

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


# --- All-injected functions (equivalent of old Form 1, now using Inject[T]) ---

async def test_all_injected_simple():
    """One parameter, one injector, returns the value."""
    def get_config():
        return Config(name="test")

    def feature(*, config: Inject[Config]):
        return config.name

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert result == "test"


async def test_all_injected_chained():
    """Injector A needs injector B; both resolve cleanly."""
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
    result = await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert result == "db_config"


async def test_all_injected_from_seed_data():
    """A type provided in seed_data is used without consulting the injectors_map."""
    def feature(*, config: Inject[Config]):
        return config.name

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    cfg = Config(name="from_root")
    result = await di.with_seed_data({Config: cfg}).async_call_with_args(fn=feature, args=(), kwargs={})
    assert result == "from_root"


async def test_all_injected_seed_data_overrides_injector():
    """When a type is in both seed_data and injectors_map, seed_data wins."""
    def get_config():
        return Config(name="from_injector")

    def feature(*, config: Inject[Config]):
        return config.name

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    cfg = Config(name="from_root")
    result = await di.with_seed_data({Config: cfg}).async_call_with_args(fn=feature, args=(), kwargs={})
    assert result == "from_root"


async def test_all_injected_missing_type_raises():
    """No value in seed_data and no injector → LookupError."""
    def feature(*, config: Inject[Config]):
        return config

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    with pytest.raises(LookupError, match="Config"):
        await di.async_call_with_args(fn=feature, args=(), kwargs={})


async def test_all_injected_circular_dependency_raises():
    """A → B → A → ... should raise RecursionError, not loop forever."""
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
        await di.async_call_with_args(fn=feature, args=(), kwargs={})


async def test_all_injected_isinstance_check_failure():
    """An injector returning the wrong type should raise TypeError."""
    def get_config():
        return "not a Config"  # wrong type

    def feature(*, config: Inject[Config]):
        return config

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    with pytest.raises(TypeError, match="not an instance"):
        await di.async_call_with_args(fn=feature, args=(), kwargs={})


async def test_all_injected_caches_per_call():
    """The same type resolved twice in one call returns the same instance."""
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
    cfg, db, db_cfg = await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert cfg is db_cfg
    assert call_count["n"] == 1


async def test_all_injected_async_injector():
    """An async injector function is awaited."""
    async def get_config():
        return Config(name="async_config")

    def feature(*, config: Inject[Config]):
        return config.name

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert result == "async_config"


async def test_all_injected_async_feature():
    """An async top-level feature function is awaited."""
    def get_config():
        return Config(name="cfg")

    async def feature(*, config: Inject[Config]):
        return config.name

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert result == "cfg"


# --- Generator-based cleanup ---

async def test_sync_generator_cleanup():
    """A sync generator injector yields once, cleanup runs after."""
    events: list[str] = []

    def get_config():
        events.append("config_setup")
        yield Config(name="from_gen")
        events.append("config_teardown")

    def feature(*, config: Inject[Config]):
        events.append("feature_running")
        return config.name

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert result == "from_gen"
    assert events == ["config_setup", "feature_running", "config_teardown"]


async def test_async_generator_cleanup():
    """An async generator injector with awaited setup/teardown."""
    events: list[str] = []

    async def get_config():
        events.append("config_setup")
        yield Config(name="async_gen")
        events.append("config_teardown")

    def feature(*, config: Inject[Config]):
        events.append("feature_running")
        return config.name

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    result = await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert result == "async_gen"
    assert events == ["config_setup", "feature_running", "config_teardown"]


async def test_cleanup_in_reverse_order():
    """Multiple cleanup generators run in reverse (LIFO) order."""
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
    await di.async_call_with_args(fn=feature, args=(), kwargs={})
    assert events == [
        "config_setup",
        "database_setup",
        "feature_running",
        "database_teardown",  # LIFO: database tears down first
        "config_teardown",
    ]


# --- call_with_args (mixed passthrough + inject) ---

async def test_call_with_args_passthrough_only():
    """No injection, just passthrough args."""
    # test-fixture-data: a command whose default fills in for an unpassed arg.
    def feature(name, times=1):   # test-fixture-data
        return f"{name}*{times}"

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = await di.async_call_with_args(
        fn=feature, args=("Alice", 3), kwargs={}
    )
    assert result == "Alice*3"


async def test_call_with_args_with_inject():
    """Mixed passthrough and injected arguments."""
    def get_ctx():
        return ReqCtx()

    def feature(name, *, ctx: Inject[ReqCtx]):
        return (name, ctx)

    di = DependencyInjector(injectors_map=make_map({"ReqCtx": get_ctx}), seed_data={})
    name, ctx = await di.async_call_with_args(
        fn=feature, args=("Alice",), kwargs={}
    )
    assert name == "Alice"
    assert isinstance(ctx, ReqCtx)


async def test_call_with_args_with_default_and_inject():
    """Defaults on passthrough work alongside injection."""
    def get_ctx():
        return ReqCtx()

    # test-fixture-data: proves a passthrough default survives injection --
    # the test asserts `times == 2` without passing it.
    def feature(name, times=2, *, ctx: Inject[ReqCtx]):   # test-fixture-data
        return (name, times, ctx)

    di = DependencyInjector(injectors_map=make_map({"ReqCtx": get_ctx}), seed_data={})
    name, times, ctx = await di.async_call_with_args(
        fn=feature, args=("Bob",), kwargs={}
    )
    assert name == "Bob"
    assert times == 2  # default used
    assert isinstance(ctx, ReqCtx)


async def test_call_with_args_kwargs_only():
    """Passing all passthrough args by keyword."""
    # test-fixture-data: a command whose default fills in for an unpassed arg.
    def feature(name, times=1):   # test-fixture-data
        return f"{name}*{times}"

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    result = await di.async_call_with_args(
        fn=feature, args=(), kwargs={"name": "Carol", "times": 5}
    )
    assert result == "Carol*5"


async def test_call_with_args_missing_required():
    """A required passthrough arg with no value raises (Python's own TypeError)."""
    def feature(name):
        return name

    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    with pytest.raises(TypeError, match="missing 1 required positional argument"):
        await di.async_call_with_args(
            fn=feature, args=(), kwargs={}
        )


# --- Signature cache ---

async def test_signature_caches_reuse():
    """Inspecting the same function twice returns the same signature object."""
    def get_config():
        return Config(name="default")

    def feature(*, config: Inject[Config]):
        return config

    di = DependencyInjector(injectors_map=make_map({"Config": get_config}), seed_data={})
    sig1 = di.cached_call_with_args_signature(feature)
    sig2 = di.cached_call_with_args_signature(feature)
    assert sig1 is sig2


async def test_bound_method_cache_key_stability():
    """Bound methods of different instances share the same cache entry."""
    class Service:
        def get_config(self) -> Config:
            return Config(name="default")

    s1 = Service()
    s2 = Service()
    di = DependencyInjector(injectors_map=make_map({}), seed_data={})
    sig1 = di.cached_call_with_args_signature(s1.get_config)
    sig2 = di.cached_call_with_args_signature(s2.get_config)
    # Same cache entry, same signature object.
    assert sig1 is sig2
