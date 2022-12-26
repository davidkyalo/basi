import typing as t
from collections import abc

from typing_extensions import Concatenate
from .base import Bus, MethodTask, Task
from . import get_current_app, bus, app, current_task

from .base import _P, _R, _T

@t.overload
def shared_task(fn: abc.Callable[_P, _R], /, **kw) -> Task[_P, _R]:
    return bus.task()

@t.overload
def shared_task(**kw) -> abc.Callable[[abc.Callable[_P, _R]], Task[_P, _R]]:
    pass

@t.overload
def shared_method_task(
    fn: abc.Callable[Concatenate[_T, _P], _R], /, *a, **kw
) -> MethodTask[_T, _P, _R]:
    pass

@t.overload
def shared_method_task(
    **kw,
) -> abc.Callable[[abc.Callable[Concatenate[_T, _P], _R]], MethodTask[_T, _P, _R]]:
    pass

shared_task = bus.task
shared_method_task = bus.method_task
