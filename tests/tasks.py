from dataclasses import dataclass, field
from datetime import datetime
from time import monotonic_ns, sleep as do_sleep
from unittest.mock import Mock, _Call
import pytest
import typing as t

from celery import Task as BaseTask, Celery, current_task, current_app
from basi.base import TaskMethod, Task
from basi import task_method


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
    def method(self, *args, **kwargs):
        assert isinstance(self, SampleTaskMethods)
        return self.mock(*args, **kwargs)

    @task_method(bind=True, app=current_app)
    def bound_method(self, task: TaskMethod, *args, **kwargs):
        assert isinstance(self, SampleTaskMethods)
        assert self.__class__.bound_method is task
        return self.mock(*args, **kwargs)
