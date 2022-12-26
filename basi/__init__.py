def __patch_typing():
    global __patch_typing
    from celery.app.task import Task
    from celery.canvas import Signature
    from celery.result import ResultBase

    for cls in [Task, ResultBase, Signature]:
        if not hasattr(cls, "__class_getitem__"):
            cls.__class_getitem__ = classmethod(lambda c, *a, **kw: c)
    del __patch_typing


__patch_typing()


import os
import typing as t
from collections import abc
from typing import TYPE_CHECKING, TypeVar, overload

import celery
from celery import current_task, current_app
from celery.local import Proxy

from ._common import import_string
from .base import Bus, TaskMethod, Task
from .serializers import SupportsPersistentPickle

current_task: Task

_T_Fn = TypeVar("_T_Fn", bound=abc.Callable)


DEFAULT_NAMESPACE = os.getenv("BASI_NAMESPACE", "CELERY")

APP_CLASS_ENVVAR = f"{DEFAULT_NAMESPACE}_APP_CLASS"
SETTINGS_ENVVAR = f"{DEFAULT_NAMESPACE}_SETTINGS_MODULE"


def get_current_app() -> Bus:
    from celery import _state

    if _state.default_app:
        return _state.get_current_app()

    cls: type[Bus] = os.getenv(APP_CLASS_ENVVAR) or Bus
    if isinstance(cls, str):
        cls = import_string(cls)

    app = cls(
        "default",
        fixups=[],
        set_as_current=False,
        namespace=DEFAULT_NAMESPACE,
        loader=os.environ.get("CELERY_LOADER") or "default",
    )
    app.set_default()
    app.config_from_envvar(SETTINGS_ENVVAR)

    from . import canvas

    return _state.get_current_app()


bus: Bus = Proxy(get_current_app)
app = bus


shared_task = celery.shared_task


class _MethodTaskProxy(Proxy):
    __slots__ = ()

    def __get__(self, obj, cls=None):
        return self._get_current_object().__get__(obj, cls)


def task_method(fn=None, /, *args, app: celery.Celery = None, base=TaskMethod, **options):
    options["base"] = base or TaskMethod
    xname = options.pop("name", None)

    def decorator(func):
        name = xname or f"{func.__module__}.{func.__qualname__}"
        if app is None:
            task = shared_task(func, *args, name=name, **options)
        else:
            task = app.task(func, *args, name=name, **options)

        return _MethodTaskProxy(lambda: task)

    return decorator if fn is None else decorator(fn)
