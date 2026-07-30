# We do not use functools.cached_property because it contains messy
# and unnecessary code for threaded programs.  In addition, our
# `@cached_property` decorator can be used correctly with async methods.

import inspect, asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar, Generic, Callable, Any, overload

T = TypeVar('T')

class cached_property(Generic[T]):
    fn: Callable[[Any], T]
    _name: str

    def __init__(self, fn: Callable[[Any], T]):
        import types
        fn2 = fn if isinstance(fn, types.FunctionType) else getattr(fn, '__call__', fn)  # type: ignore[arg-type]
        if inspect.iscoroutinefunction(fn2):
            self.fn = lambda self: create_task_loop_check(fn(self), name=None, context=None)  # type: ignore[assignment,return-value]
        else:
            self.fn = fn
        self._name = fn.__name__
        self.__doc__ = fn.__doc__

    @overload
    def __get__(self, instance: None, cls: type) -> cached_property[T]: ...
    @overload
    def __get__(self, instance: object, cls: type) -> T: ...

    def __get__(self, instance: object | None, cls: type) -> T | cached_property[T]:
        if instance is None:
            return self
        value = self.fn(instance)
        instance.__dict__[self._name] = value
        return value

def create_task_loop_check(coro: Any, name: str | None, context: Any) -> LoopCheck:
    task = asyncio.create_task(coro, name=name, context=context)
    task._loop_check_parent_task = asyncio.current_task()  # type: ignore[attr-defined]
    return LoopCheck(task=task)

@dataclass(frozen=True)
class LoopCheck:
    task: asyncio.Task[Any]

    def __await__(self):
        testing = asyncio.current_task()
        while testing:
            if testing is self.task:
                raise ValueError(f'Deadlock: {self.task}')
            testing = getattr(testing, '_loop_check_parent_task', None)
        return self.task.__await__()
