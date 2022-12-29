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
from types import new_class

import celery
from celery import current_app, current_task, shared_task
from celery.local import Proxy
from typing_extensions import Concatenate as Concat
from typing_extensions import ParamSpec

from ._common import import_string
from .base import _P, _R, _T, Bus, Task, TaskClassMethod, TaskMethod
from .serializers import SupportsPersistentPickle

current_task: Task

_T = t.TypeVar("_T")
_R = t.TypeVar("_R")
_P = ParamSpec("_P")


_T_Fn = abc.Callable



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


class _MethodTaskProxy(Proxy):
    __slots__ = ()

    def __get__(self, obj, cls=None):
        return self._get_current_object().__get__(obj, cls)



@t.overload
def task_method(fn: _T_Fn[Concat[_T, _P], _R], /, *a, **kw) -> TaskMethod[_T, _P, _R]: ...
@t.overload
def task_method(**kw) -> _T_Fn[[_T_Fn[Concat[_T, _P], _R]], TaskMethod[_T, _P, _R]]: ...

def task_method(fn=None, /, *args, name: str=None, app: celery.Celery = None, bind: bool=False, base: type[celery.Task]=None, **options):
    """Decorator to create a TaskMethod class out of any callable.

        See :ref:`Task options<task-options>` for a list of the
        arguments that can be passed to this decorator.
        If `app` is not provided (the default), the returned task is created 
        by calling `celery.shared_task()`. Otherwise `app.task()` will be called.

        Examples:
            .. code-block:: python

                @task_method
                def refresh_feed(url):
                    store_feed(feedparser.parse(url))

            with setting extra options:

            .. code-block:: python

                @task_method(exchange='feeds', app=celery_app)
                def refresh_feed(url):
                    return store_feed(feedparser.parse(url))

        Note:
            App Binding: For custom apps the task decorator will return
            a proxy object, so that the act of creating the task is not
            performed until the task is used or the task registry is accessed.

            If you're depending on binding to be deferred, then you must
            not access any attributes on the returned object until the
            application is fully set up (finalized).
        """

    options["base"] = base or TaskMethod
    if base and not issubclass(base, TaskMethod):
        options["base"] = new_class(base.__name__, (TaskMethod, base), None, lambda ns: ns.update(__module__=base.__module__))
    if bind:
        options['bind_task_instance'] = True
        
    def decorator(func):
        options["name"] = name or f"{func.__module__}.{func.__qualname__}"
        if app is None:
            task = shared_task(func, *args, **options)
        else:
            task = app.task(func, *args, **options)

        return _MethodTaskProxy(lambda: task)

    return decorator if fn is None else decorator(fn)




@t.overload
def task_class_method(fn: _T_Fn[Concat[type[_T], _P], _R], /, *a, **kw) -> TaskClassMethod[_T, _P, _R]: ...
@t.overload
def task_class_method(**kw) -> _T_Fn[[_T_Fn[Concat[type[_T], _P], _R]], TaskClassMethod[_T, _P, _R]]: ...

def task_class_method(*a, base: type[celery.Task]=None, **options):
    options["base"] = base or TaskClassMethod
    if base and not issubclass(base, TaskClassMethod):
        options["base"] = new_class(base.__name__, (TaskClassMethod, base), None, lambda ns: ns.update(__module__=base.__module__),)
    return task_method(*a, **options)


