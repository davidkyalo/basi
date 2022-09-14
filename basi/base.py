from collections import abc
from functools import cache
from typing import TYPE_CHECKING, Any, Literal, Union, overload
from celery import Celery, Task as BaseTask
from celery.canvas import Signature
from celery.app import push_current_task, pop_current_task
from celery.app.base import gen_task_name
from celery.worker.request import Context

from basi._common import import_string


class Task(BaseTask):

    request: Context
    app: "Bus"
    is_method: bool = False

    if TYPE_CHECKING:
        def resolve_arguments(self, *args, **kwargs) -> tuple[tuple, dict[str, Any]]:
            pass
    else:
        resolve_arguments = None

    def __call__(self, /, *args, **kwargs):
        push_current_task(self)
        self.push_request(args=args, kwargs=kwargs)
        try:
            if self.resolve_arguments:
                args, kwargs = self.resolve_arguments(*args, **kwargs)
            return self.run(*args, **kwargs)
        finally:
            self.pop_request()
            pop_current_task()



# class BoundSignature(Signature):
#     __slots__ = ()

#     def __call__(self, /, *args: Any, **kwds: Any) -> Any:
#         return super().__call__(*args, **kwds)

#     def apply_async(self, args=None, kwargs=None, route_name=None, **options):
#         return super().apply_async(args, kwargs, route_name, **options)

#     def apply(self, args=None, kwargs=None, **options):
#         return super().apply(args, kwargs, **options)


_missing = object()

class BoundTask(Task):

    def resolve_arguments(self, /, *args, __self__=_missing, **kwargs):
        if __self__ is _missing:
            __self__, args = (args or (None,))[0], args[1:]
        return (self.resolve_self(__self__),) + args, kwargs

    def resolve_self(self, /, s):
        return s




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



Celery = Bus




