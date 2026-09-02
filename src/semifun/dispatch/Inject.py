from dataclasses import dataclass, field
from inspect import signature
from typing import get_args, get_origin

type Inject[T] = T


def injected_type(annotation) -> type | None:
    """If annotation is Inject[T], return T. Otherwise return None."""
    if get_origin(annotation) is Inject:
        args = get_args(annotation)
        if len(args) == 1:
            return args[0]
    return None


def signature_without_Inject(fn):
    """Return fn's signature with Inject[…] parameters removed."""
    sig = signature(fn)
    return sig.replace(parameters=[
        p for p in sig.parameters.values()
        if injected_type(p.annotation) is None
    ])

@dataclass(frozen=True)
class parametric_type:
    """Create a parameterized type for use with Inject[...].

        DB = parametric_type('DB')

        def get_items(db: Inject[DB('items')], user_db: Inject[DB('users')]):
            ...

    Each distinct set of arguments produces a distinct (but equal-by-value)
    instance, so the DI cache resolves each variant separately.
    """
    name: str

    def __call__(self, *args, **kwargs) -> _ParametricInstance:
        return _ParametricInstance(
            __name__=self.name,
            hash_key=(self.name, args, tuple(sorted(kwargs.items()))),
            dependency_injection_args2=(args, kwargs),
        )

@dataclass(frozen=True)
class _ParametricInstance:
    """A parameterized DI type, e.g. DB('users').

    Works with resolve_type: __name__ for lookup, dependency_injection_args2
    for passing args/kwargs to the factory.
    """
    hash_key: tuple
    dependency_injection_args2: tuple = field(hash=False, compare=False)
    __name__: str = field(hash=False, compare=False)


