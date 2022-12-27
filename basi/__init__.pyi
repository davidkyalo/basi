import typing as t
from collections import abc

from typing_extensions import Concatenate as Concat

import basi

from . import TaskClassMethod, TaskMethod
from .base import _P, _R, _T

_T_Fn = abc.Callable[_P, _R]

@t.overload
def task_method(fn: _T_Fn[Concat[_T, _P], _R], /, *a, **kw) -> TaskMethod[_T, _P, _R]: ...
@t.overload
def task_method(**kw) -> _T_Fn[[_T_Fn[Concat[_T, _P], _R]], TaskMethod[_T, _P, _R]]: ...

task_method = basi.task_method



@t.overload
def task_class_method(fn: _T_Fn[Concat[type[_T], _P], _R], /, *a, **kw) -> TaskClassMethod[_T, _P, _R]: ...
@t.overload
def task_class_method(**kw) -> _T_Fn[[_T_Fn[Concat[type[_T], _P], _R]], TaskClassMethod[_T, _P, _R]]: ...

task_class_method = basi.task_class_method