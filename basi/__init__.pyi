import typing as t
from collections import abc

from typing_extensions import Concatenate as Concat
from .base import Bus, TaskMethod, Task
from . import get_current_app, bus, app, current_task, current_app

from .base import _P, _R, _T

_T_Fn = abc.Callable[_P, _R]

@t.overload
def shared_task(fn: _T_Fn[_P, _R], /, **kw) -> Task[_P, _R]: ...
@t.overload
def shared_task(**kw) -> _T_Fn[[_T_Fn[_P, _R]], Task[_P, _R]]: ...

shared_task = app.task

@t.overload
def task_method(fn: _T_Fn[Concat[_T, _P], _R], /, *a, **kw) -> TaskMethod[_T, _P, _R]: ...
@t.overload
def task_method(**kw) -> _T_Fn[[_T_Fn[Concat[_T, _P], _R]], TaskMethod[_T, _P, _R]]: ...

task_method = app.task
