import typing as t
from dataclasses import asdict, dataclass, field
from datetime import datetime
from time import monotonic_ns
from time import sleep as do_sleep
from unittest.mock import Mock, _Call

import pytest
from celery import Celery
from celery import Task as BaseTask
from celery import current_app, current_task

from basi import task_class_method, task_method
from basi.base import TaskMethod


class WaitMock(Mock):
    def wait_for_call(self, call: _Call = None, start=0, timeout=4, sleep=5e-9):
        initial_calls, count = [*self.call_args_list[:start]], start + 1
        stop = monotonic_ns() + int(timeout * 1e9)
        while not (self.call_count >= count or monotonic_ns() > stop):
            sleep and do_sleep(sleep)
        assert self.call_count == count, f""
        call is None or self.assert_has_calls([*initial_calls, call])


@dataclass
class SampleTaskMethods:
    foo: str = field(default_factory=lambda: datetime.now().time().isoformat())
    bar: str = field(default_factory=lambda: datetime.now().date().isoformat())

    mock: t.ClassVar = WaitMock()

    @task_method
    def simple_task(self, *args, **kwargs):
        assert isinstance(self, SampleTaskMethods)
        return self.mock(*args, **kwargs)

    @task_method(bind=True)
    def bound_task(self, task: TaskMethod, *args, **kwargs):
        assert isinstance(self, SampleTaskMethods)
        assert self.__class__.bound_task is task
        return self.mock(*args, **kwargs)

    @task_method(bind=True)
    def typed_task(self, task: TaskMethod, /, foo: str, bar: int):
        assert isinstance(self, SampleTaskMethods)
        assert self.__class__.typed_task is task
        return self.mock(foo, bar)


@dataclass
class SampleTaskClassMethods:
    foo: str = field(default_factory=lambda: datetime.now().time().isoformat())
    bar: str = field(default_factory=lambda: datetime.now().date().isoformat())

    mock: t.ClassVar = WaitMock()

    @task_class_method
    def simple_task(cls, *args, **kwargs):
        assert cls is SampleTaskClassMethods
        return cls.mock(*args, **kwargs)

    @task_class_method(bind=True)
    def bound_task(cls, task: TaskMethod, *args, **kwargs):
        assert cls is SampleTaskClassMethods
        assert cls.bound_task == task
        return cls.mock(*args, **kwargs)

