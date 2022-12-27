from ast import arg
from collections import abc
from functools import cached_property, partial
from typing import TYPE_CHECKING, Any, Final, Generic, TypeVar, Union, cast, overload
from uuid import uuid4

from celery import states, shared_task
from celery.canvas import Signature, group

# from celery.exceptions import TaskPredicate, Ignore, Retry, Reject
from celery.result import AsyncResult, EagerResult
from celery.utils.abstract import CallableTask
from celery.utils.objects import getitem_property
from kombu.utils.uuid import uuid
from typing_extensions import ParamSpec, Self
from vine import Thenable, promise


_P = ParamSpec("_P")
_R = TypeVar("_R")
_T = TypeVar("_T")

_empty = object()


if TYPE_CHECKING:
    cached_property = property
    from basi.base import Task


def _apply_async(self, *a, **kw):
    return self.apply(*a, **kw)


def _to_result_(result: Union[_R, EagerResult], id=None, state=None, traceback=None):
    rv: EagerResult
    if isinstance(result, AsyncResult):
        assert None is id is state is traceback
        rv = result
    else:
        if id is None:
            id = uuid()
        if state is None:
            state = states.FAILURE if isinstance(result, Exception) else states.SUCCESS
        rv = EagerResult(id, result, state, traceback)
    return rv


def _wait_for_result_(result: EagerResult, *args, **kwds):
    return result.get(*args, **kwds)


@shared_task(name=f"{__package__}.run_in_worker")
def run_in_worker(func: abc.Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R:
    return func(*args, **kwargs)


@shared_task(name=f"{__package__}.wrap", bind=True)
def wrap(self, func: abc.Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R:
    if not callable(func):
        raise TypeError(f"{self.name!r} expected a callable not {func.__class__.__name__!r}")
    return func(*args, **kwargs)


@shared_task(name=f"{__package__}.throw")
def throw(cls: type[Exception], *args, **kwargs):
    raise (cls if isinstance(cls, Exception) else cls(*args, **kwargs))


@CallableTask.register
class ValuePseudoTask(Generic[_R]):
    """A signature that always executes eagerly."""

    __slots__ = "name", "result", "state", "traceback", "__weakref__"
    name: str
    result: _R
    _wrap_states = [(states.SUCCESS, "link"), (states.FAILURE, "link_error")]

    def __new__(cls, result: _R, state=None, traceback=None, name=None):
        self = object.__new__(cls)
        self.name, self.result, self.state, self.traceback = name, result, state, traceback
        return self

    def EagerResult(self, tid=None):
        return _to_result_(self.result, tid, self.state, self.traceback)

    AsyncResult = EagerResult

    def delay(self, *args, **kwargs):
        return self.apply(args, kwargs)

    def apply_async(self, *a, task_id: str = None, **kw):
        print(vars())
        kw["task_id"] = task_id = task_id or self.name or str(uuid4())
        if kw.get("reply_to"):
            return wrap.s(_wait_for_result_, self.EagerResult(task_id)).apply_async(*a, **kw)
        return self.apply(*a, **kw)

    def apply(self, args=(), kwargs=None, task_id: str = None, **kwds):
        kwds["task_id"] = task_id = task_id or self.name or str(uuid4())
        result = self.EagerResult(task_id)
        state = result.state
        if any(not (state != s or kwds.get(k) is None) for s, k in self._wrap_states):
            return wrap.s(_wait_for_result_, result).apply(**kwds)
        return result

    def __call__(self, *args, **kwds):
        return self.EagerResult().get()


class SubtaskType(Signature, Generic[_R]):
    __slots__ = ()

    _subtask_type_ = None

    def __init_subclass__(cls, name: Union[str, None] = None) -> None:
        cls._subtask_type_ = name = cast(
            str, name or cls.__dict__.get("_subtask_type_", cls.__name__)
        )
        if cls._subtask_type_:
            Signature.register_type(name)(cls)
        super().__init_subclass__()

    @classmethod
    def from_dict(cls, d, app=None):
        return cls(d, app=app)

    @property
    def subtask_type(self):
        return self._subtask_type_

    if not TYPE_CHECKING:

        def __init__(self, *a, **kw) -> None:
            super().__init__(*a, subtask_type=self._subtask_type_, **kw)

    else:

        def apply(self, *args, **kwds) -> "EagerResult[_R]":
            ...

        def apply_async(self, *args, **kwds) -> "AsyncResult[_R]":
            ...

        def __call__(self, *args, **kwds) -> _R:
            ...


class result(SubtaskType[_R], name="result"):
    """A signature that always executes eagerly."""

    def __init__(self, result: _R = None, *args, app=None, **kwargs):
        if not (not app is _empty and isinstance(result, dict) and "subtask_type" in result):
            result = ValuePseudoTask(result, name="result")
            # kwargs.setdefault('serializer', 'pickle')
        app is _empty or kwargs.update(app=app)
        super().__init__(result, *args, **kwargs)


class eager(SubtaskType[_R], Generic[_R]):
    """A signature that always executes eagerly."""

    if not TYPE_CHECKING:
        apply_async = _apply_async


del _apply_async
