from dataclasses import dataclass
import pytest
import typing as t

from celery import Task as BaseTask, Celery
from basi.base import MethodTask, Task


@pytest.mark.usefixtures("celery_session_app", "celery_session_worker")
class test_TaskMethod:
    args = args, kwargs = ("foo", "bar"), dict(a=1, b=2, c=3)

    def new(self, *a, **kw):
        from .tasks import Klass

        return Klass(*a, **kw)

    @pytest.fixture()
    def obj(self):
        return self.new()

    @pytest.fixture(params=["simple_task", "bound_task"])
    def task(self, request: pytest.FixtureRequest, obj):
        return getattr(obj, request.param)

    def test_apply(self, obj, task: MethodTask):
        args, kwargs = self.args, self.kwargs
        res = task.apply(args, kwargs)
        r_obj, r_args, r_kwargs = res.get()
        assert r_obj == obj
        assert r_args == args
        assert r_kwargs == kwargs

    def test_apply_async(self, obj, task: MethodTask):
        args, kwargs = self.args, self.kwargs
        res = task.apply_async(args, kwargs)
        r_obj, r_args, r_kwargs = res.get()
        assert r_obj == obj
        assert r_args == args
        assert r_kwargs == kwargs

    def test_delay(self, obj, task: MethodTask):
        args, kwargs = self.args, self.kwargs
        res = task.delay(*args, **kwargs)
        r_obj, r_args, r_kwargs = res.get()
        assert r_obj == obj
        assert r_args == args
        assert r_kwargs == kwargs

    def test_call(self, obj, task: MethodTask):
        args, kwargs = self.args, self.kwargs
        res = task.delay(*args, **kwargs)
        r_obj, r_args, r_kwargs = res.get()
        assert r_obj == obj
        assert r_args == args
        assert r_kwargs == kwargs
