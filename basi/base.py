from collections import abc
from functools import cache, cached_property, wraps
from logging import Logger
from types import FunctionType, MethodType
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, Union, overload
from typing_extensions import Self
from celery import Celery, Task as BaseTask
from celery.canvas import Signature
from celery.app import push_current_task, pop_current_task
from celery.app.base import gen_task_name
from celery.worker.request import Context
from celery.local import Proxy
from celery.utils.log import get_task_logger

from basi._common import import_string

BaseTask.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)

class Task(BaseTask):

    request: Context
    app: "Bus"
    logger: Logger

    @cached_property
    def logger(self):
        return get_task_logger(self.__module__)



_missing = object()
_T = TypeVar('_T')


class MethodTask(Task, Generic[_T]):

    bind_task = None
    method: str = None
    attr_name: str = None
    BoundProxy: type['BoundMethodTaskProxy'] = None

    def __init_subclass__(cls, **kwargs) -> None:
        if 'run' in cls.__dict__:
            cls.bind_task = not isinstance(cls.__dict__['run'], staticmethod) or cls.bind_task
            fn = cls.run
            @wraps(fn)
            def run(self: Self=..., /, *a, **kw):
                nonlocal fn
                a, kw = self.resolve_arguments(a, kw)
                if self.bind_task:
                    a = a[:1] + (self,) + a[1:]
                return fn(*a, **kw)
            cls.run = run
        return super().__init_subclass__(**kwargs)

    def __get__(self, obj: _T, typ) -> Self:
        if obj is None:
            return self
        return self.get_bound_instance(obj)

    def get_bound_instance(self, obj):
        return self.BoundProxy(self, obj)

    def resolve_arguments(self, /, args, kwargs):
        __self__ = self.resolve_self(args, kwargs)
        if not __self__ is _missing:
            args = (__self__,)  + args
        return args, kwargs

    def resolve_self(self, args: tuple, kwargs: dict):
        return kwargs.pop('__self__', _missing)

    def contribute_to_class(self, cls, name):
        setattr(cls, self.attr_name or name, self)




class BoundMethodTaskProxy(Proxy, (MethodTask[_T] if TYPE_CHECKING else Generic[_T])):

    __slots__ = ()

    def __init__(self, task: MethodTask, obj: _T=_missing, /, **kwargs):
        super().__init__(task, kwargs={ '__self__': obj } | kwargs)

    def _get_current_object(self) -> MethodTask:
        return object.__getattribute__(self, '_Proxy__local')

    def _get_current_kwargs(self, kwargs=None):
        return object.__getattribute__(self, '_Proxy__kwargs') | (kwargs or {})
    
    if not TYPE_CHECKING:
        def s(self, *args, **kwargs):
            return self.signature(args, kwargs)
        
        def si(self, *args, **kwargs):
            return self.signature(args, kwargs, immutable=True)

        def signature(self, args=None, kwargs=None, *starargs, **starkwargs):
            kwargs = self._get_current_kwargs(kwargs)
            return self._get_current_object().signature(args, kwargs, *starargs, **starkwargs)
        
        subtask = signature

        def delay(self, *args, **kwargs):
            return self.apply_async(args, kwargs)
        
        @overload
        def apply(self, args=None, kwargs=None, link=None, link_error=None, task_id=None, retries=None, throw=None, logfile=None, loglevel=None, headers=None, **options): ...
        def apply(self, args=None, kwargs=None, *__args, **options):
            kwargs = self._get_current_kwargs(kwargs)
            return self._get_current_object().apply(args, kwargs, *__args, **options)

        @overload
        def apply_async(self, args=None, kwargs=None, task_id=None, producer=None, link=None, link_error=None, shadow=None, **options):...
        def apply_async(self, args=None, kwargs=None, *__args, **options):
            kwargs = self._get_current_kwargs(kwargs)
            return self._get_current_object().apply_async(args, kwargs, *__args, **options)

        def __call__(self, *args, **kwargs):
            kwargs = self._get_current_kwargs(kwargs)
            return self._get_current_object()(*args, **kwargs)



MethodTask.BoundProxy = BoundMethodTaskProxy



class Bus(Celery):

    queue_prefix_separator: str = "::"

    @overload
    def __init__(
        self,
        main=None,
        loader=None,
        backend=None,
        amqp=None,
        events=None,
        log=None,
        control=None,
        set_as_current=True,
        tasks=None,
        broker=None,
        include=None,
        changes=None,
        config_source=None,
        fixups=None,
        task_cls: type[str] = Task,
        autofinalize=True,
        namespace=None,
        strict_typing=True,
        **kwargs,
    ):
        ...

    def __init__(self, *args, task_cls: type[str] = Task, **kwargs):

        if isinstance(task_cls, str):
            task_cls = import_string(task_cls)
        
        super().__init__(
            *args,
            task_cls=task_cls,
            **kwargs
        )
        
    def get_workspace_prefix(self) -> Union[str, None]:
        return ""

    def gen_task_name(self, name, module):
        return f"{self.get_workspace_prefix()}{self.get_task_name_func()(self, name, module)}"

    @cache
    def get_task_name_func(self):
        if fn := self.conf.get("task_name_generator"):
            if isinstance(fn, str):
                fn = self.conf["task_name_generator"] = import_string(fn)
            return fn
        return gen_task_name

    if TYPE_CHECKING:

        def task(self, *args, **opts) -> abc.Callable[..., Task]:
            ...

    @overload
    def send_task(
        self,
        name,
        args=None,
        kwargs=None,
        countdown=None,
        eta=None,
        task_id=None,
        producer=None,
        connection=None,
        router=None,
        result_cls=None,
        expires=None,
        publisher=None,
        link=None,
        link_error=None,
        add_to_parent=True,
        group_id=None,
        group_index=None,
        retries=0,
        chord=None,
        reply_to=None,
        time_limit=None,
        soft_time_limit=None,
        root_id=None,
        parent_id=None,
        route_name=None,
        shadow=None,
        chain=None,
        task_type=None,
        **options,
    ):
        ...

    def send_task(self, name: str, *args, **kwds):
        q, _, name = name.rpartition(self.queue_prefix_separator)
        q and kwds.update(queue=q)
        return super().send_task(name, *args, **kwds)

    def method_task(self, fn=None, /, *args, base=MethodTask, **opts):
        """Decorator to create a MethodTask class out of any callable.

        See :ref:`Task options<task-options>` for a list of the
        arguments that can be passed to this decorator.

        Examples:
            .. code-block:: python

                @app.method_task
                def refresh_feed(url):
                    store_feed(feedparser.parse(url))

            with setting extra options:

            .. code-block:: python

                @app.method_task(exchange='feeds')
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
        opts['base'] = base or MethodTask
        def decorator(func):
            return self.task(func, *args, **{'name': f'{func.__module__}.{func.__qualname__}'} | opts)
        return decorator if fn is None else decorator(fn)



Celery = Bus




