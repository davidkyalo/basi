from collections import abc
from functools import cache
from typing import TYPE_CHECKING, Literal, Union, overload
from celery import Celery, Task as BaseTask
from celery.app.base import gen_task_name
from celery.worker.request import Context

from basi._common import import_string


class Task(BaseTask):

    request: Context
    app: "Bus"

    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


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




