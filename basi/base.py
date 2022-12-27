from collections import ChainMap, abc
from functools import cache, cached_property, wraps
from logging import Logger
from types import FunctionType, GenericAlias, MethodType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    Optional,
    TypeVar,
    Union,
    overload,
)

from celery import Celery
from celery.app import pop_current_task, push_current_task
from celery.app.base import gen_task_name
from celery.app.task import Context
from celery.app.task import Task as BaseTask
from celery.canvas import Signature
from celery.local import Proxy
from celery.utils.log import get_task_logger
from typing_extensions import Concatenate, ParamSpec, Self

from basi._common import import_string

_missing = object()
_T = TypeVar("_T")
_R = TypeVar("_R")
_P = ParamSpec("_P")


class Task(BaseTask, Generic[_T, _P, _R]):

    # __class_getitem__ = classmethod(GenericAlias)

    request: Context
    app: "Bus"
    logger: Logger

    @cached_property
    def logger(self):
        return get_task_logger(self.__module__)

class TaskMethod(Task[_T, _P, _R]):

    bind_task_instance: bool = None
    method: staticmethod
    # typing: bool = True
    attr_name: str = None
    BoundProxy: type["BoundMethodTaskProxy"] = None
    self_key = '__self__'

    # def __init_subclass__(cls, **opts) -> None:
    #     if "run" in cls.__dict__:
    #         cls.bind_task = not isinstance(cls.__dict__["run"], staticmethod) or cls.bind_task
    #         # cls.run = staticmethod(cls.run)
    #         xrun = cls.run

    #         def run(self: TaskMethod, *args, **kwargs):
    #             nonlocal xrun
    #             args, kwargs = self.resolve_arguments(args, kwargs)
    #             if self.bind_task:
    #                 args = args[:1] + (self,) + args[1:]
    #             return self.method(*args, **kwargs)

    #         cls.run = run
    #         cls.method = staticmethod(xrun)

    #     return super().__init_subclass__(**opts)

    def __get__(self, obj: _T, typ) -> Self:
        if obj is None:
            return self
        return self.get_bound_instance(obj)

    def get_bound_instance(self, obj):
        return self.BoundProxy(self, obj)

    def resolve_call_params(self, args: tuple, kwargs: dict, *, in_transit: bool=False):
        this, bind = kwargs.pop(self.self_key, _missing), self.bind_task_instance
        if not this is _missing:
            if bind:
                if in_transit:
                    args = (this, f"<@BoundTask: {self.name!r} in transit>") + args
                else:
                    args = (this, self) + args
            else:
                args = (this,) + args
        elif bind and not in_transit:
            args = args[:1] + (self,) + args[2:]
                
        return args, kwargs

    # def resolve_self(self, args: tuple, kwargs: dict):
    #     return kwargs.pop("__self__", _missing)

    def contribute_to_class(self, cls, name):
        setattr(cls, self.attr_name or name, self)

    def __call__(self: Self, *args, **kwargs):
        args, kwargs = self.resolve_call_params(args, kwargs)
        return super().__call__(*args, **kwargs)

    def apply_async(self, args=(), kwargs: dict=None, *a, **kw):
        args, kwargs = self.resolve_call_params(args or (), kwargs or {}, in_transit=True)
        return super().apply_async(args, kwargs, *a, **kw)


class TaskClassMethod(TaskMethod[_T, _P, _R]):
    def __get__(self, obj: Optional[_T], typ: type[_T]) -> Self:
        return self.get_bound_instance(typ if obj is None else obj.__class__)


class BoundMethodTaskProxy(
    Proxy, (TaskMethod[_T, _P, _R] if TYPE_CHECKING else Generic[_T, _P, _R])
):

    __slots__ = ()

    def __init__(self, task: TaskMethod, obj: _T = _missing, /, **kwargs):
        super().__init__(task, kwargs={task.self_key: obj} | kwargs)

    def _get_current_object(self) -> TaskMethod:
        return object.__getattribute__(self, "_Proxy__local")

    def _get_current_kwargs(self, kwargs=None):
        return object.__getattribute__(self, "_Proxy__kwargs") | (kwargs or {})

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
    def apply(
        self,
        args=None,
        kwargs=None,
        link=None,
        link_error=None,
        task_id=None,
        retries=None,
        throw=None,
        logfile=None,
        loglevel=None,
        headers=None,
        **options,
    ):
        ...

    def apply(self, args=None, kwargs=None, *__args, **options):
        kwargs = self._get_current_kwargs(kwargs)
        return self._get_current_object().apply(args, kwargs, *__args, **options)

    @overload
    def apply_async(
        self,
        args=None,
        kwargs=None,
        task_id=None,
        producer=None,
        link=None,
        link_error=None,
        shadow=None,
        **options,
    ):
        ...

    def apply_async(self, args=None, kwargs=None, *__args, **options):
        kwargs = self._get_current_kwargs(kwargs)
        return self._get_current_object().apply_async(args, kwargs, *__args, **options)

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        kwargs = self._get_current_kwargs(kwargs)
        return self._get_current_object()(*args, **kwargs)

    def signature_from_request(self, request=None, args=None, kwargs=None, *__args, **options):
        kwargs = self._get_current_kwargs(kwargs)
        return self._get_current_object().signature_from_request(
            request, args, kwargs, *__args, **options
        )


TaskMethod.BoundProxy = BoundMethodTaskProxy


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
        from warnings import warn
        warn(f'`{self.__class__.__name__}()` is deprecated in favor of `Celery()`', DeprecationWarning, 1)

        if isinstance(task_cls, str):
            task_cls = import_string(task_cls)

        super().__init__(*args, task_cls=task_cls, **kwargs)

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

    @overload
    def method_task(
        self,
        fn: abc.Callable[Concatenate[_T, _P], _R],
        /,
        *args,
        base=TaskMethod[_T, _P, _R],
        get_bound_instance=None,
        **opts,
    ) -> TaskMethod[_T, _P, _R]:
        ...

    @overload
    def method_task(
        self,
        fn: None = None,
        /,
        *args,
        base=TaskMethod[_T, _P, _R],
        get_bound_instance=None,
        **opts,
    ) -> abc.Callable[[abc.Callable[Concatenate[_T, _P], _R]], TaskMethod[_T, _P, _R]]:
        ...

    def method_task(
        self, *args,
        **kwargs
    ):
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
        from warnings import warn

        from . import task_method
        
        warn(f'`{self.__class__.__name__}.method_task()` is deprecated in favor of `task_method()`', DeprecationWarning, 1)
        return task_method(*args, app=self, **kwargs)

        # opts["base"] = base or TaskMethod
        # if get_bound_instance:
        #     opts["get_bound_instance"] = get_bound_instance

        # def decorator(func: abc.Callable[_P, _R]) -> TaskMethod[_T, _P, _R]:
        #     return self.task(*args, **{"name": f"{func.__module__}.{func.__qualname__}"} | opts)(
        #         func
        #     )

        # if fn is None:
        #     return decorator
        # else:
        #     return decorator(fn)

    @overload
    def class_method_task(
        self,
        fn: abc.Callable[Concatenate[type[_T], _P], _R],
        /,
        *args,
        base=TaskClassMethod[_T, _P, _R],
        get_bound_instance=None,
        **opts,
    ) -> TaskClassMethod[_T, _P, _R]:
        ...

    @overload
    def class_method_task(
        self,
        fn: None = None,
        /,
        *args,
        base=TaskClassMethod[_T, _P, _R],
        get_bound_instance=None,
        **opts,
    ) -> abc.Callable[[abc.Callable[Concatenate[type[_T], _P], _R]], TaskClassMethod[_T, _P, _R]]:
        ...

    def class_method_task(
        self,
        *args,
        **kwargs
    ):
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
        from warnings import warn

        from . import task_class_method
        
        warn(f'`{self.__class__.__name__}.method_task()` is deprecated in favor of `task_method()`', DeprecationWarning, 1)
        return task_class_method(*args, app=self, **kwargs)

        # opts["base"] = base or ClassMethodTask
        # if get_bound_instance:
        #     opts["get_bound_instance"] = get_bound_instance

        # def decorator(
        #     func: abc.Callable[Concatenate[type[_T], _P], _R]
        # ) -> ClassMethodTask[_T, _P, _R]:
        #     return self.task(*args, **{"name": f"{func.__module__}.{func.__qualname__}"} | opts)(
        #         func
        #     )

        # if fn is None:
        #     return decorator
        # else:
        #     return decorator(fn)


Celery = Bus
