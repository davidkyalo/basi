from dataclasses import dataclass, field
from time import time
import pytest
import typing as t

from celery import Task as BaseTask, Celery, current_task, current_app
from basi.base import MethodTask, Task
from basi import shared_method_task


# app: Celery = current_app._get_current_object()


@dataclass
class Klass:
    foo: str = None
    bar: str = field(default_factory=time)

    @shared_method_task
    def simple_task(self, *args, **kwargs):
        cls, task, request = self.__class__, current_task, current_task.request
        assert isinstance(self, cls)
        return self, args, kwargs

    @shared_method_task(bind=True)
    def bound_task(self, task, *args, **kwargs):
        cls, request = self.__class__, task.request
        assert isinstance(self, cls)
        assert task is cls.bound_task
        return self, args, kwargs
