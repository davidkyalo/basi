from functools import cache
from typing import TYPE_CHECKING, Literal, Union
from celery import Celery, Task as BaseTask
from celery.app.base import gen_task_name

from basi._common import import_string


class Task(BaseTask):

    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)



class Bus(Celery):

    workspace_prefix_separator: str = ':'

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
        task_cls: type[str]=Task,
        autofinalize=True,
        namespace=None,
        strict_typing=True,
        workspace_prefix_separator=None,
        **kwargs,
    ):
        if isinstance(task_cls, str):
            task_cls = import_string(task_cls)
        super().__init__(
            main,
            loader,
            backend,
            amqp,
            events,
            log,
            control,
            set_as_current,
            tasks,
            broker,
            include,
            changes,
            config_source,
            fixups,
            task_cls,
            autofinalize,
            namespace,
            strict_typing,
            **kwargs,
        )
        if not workspace_prefix_separator is None:
            self.workspace_prefix_separator: str = workspace_prefix_separator

    @property
    @cache
    def workspace(self) -> Union[str, None]:
        return self.conf.get('workspace')

    @cache
    def get_workspace_prefix(self) -> Union[str, None]:
        if workspace := self.workspace:
            return f"{workspace}{self.workspace_prefix_separator}"
        return ''

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
        def task(self, *args, **opts) -> Task:
            ...


Celery = Bus