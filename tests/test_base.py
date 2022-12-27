from collections import abc
from dataclasses import dataclass
from functools import cached_property
from operator import eq
import sys
from time import monotonic, monotonic_ns, sleep
from unittest.mock import call
from uuid import uuid4
import pytest
import typing as t

from celery import Task as BaseTask, Celery
from celery.canvas import group
from celery.result import AsyncResult
from basi.base import TaskMethod, Task
from basi.canvas import result, throw, wrap
from basi.testing import AnyThing, TestError
from celery.app.task import Context

if t.TYPE_CHECKING:
    cached_property = property
    from tests.tasks import SampleTaskMethods


pytestmark = [
    pytest.mark.usefixtures("celery_session_app", "celery_session_worker"),
]

# @pytest.fixture(autouse=True)
# def zzz_reset_sample_task_methods_mocks():
#     from .tasks import SampleTaskMethods

#     yield
#     SampleTaskMethods.reset_mock()


class test_TaskMethod:
    @cached_property
    def args(self):
        ns = monotonic_ns
        return f"{ns()}_arg_0", f"{ns()}_arg_1", f"{ns()}_arg_2", f"{ns()}_arg_3"

    @cached_property
    def kwargs(self):
        return dict(at=monotonic_ns(), bat="bee", cat=list(range(2)))

    def new(self, *a, **kw):
        from .tasks import SampleTaskMethods as cls

        cls.mock.reset_mock(return_value=True)
        cls.mock.return_value = "|".join(f"{monotonic_ns()}" for i in range(3))
        return cls(*a, **kw)

    @pytest.fixture()
    def obj(self):
        return self.new()

    @pytest.fixture(params=["method", "bound_method"])
    def task(self, request: pytest.FixtureRequest, obj):
        return getattr(obj, request.param)

    def test_apply(self, obj: "SampleTaskMethods", task: TaskMethod):
        a, kw, mock = self.args, self.kwargs, obj.mock
        for res in [task.apply(a, kw), task.s(*a[2:], **kw).apply(a[:2])]:
            val = res.get()
            assert mock.return_value == val
        mock.assert_has_calls([call(*a, **kw)] * 2)

    def test_apply_async(self, obj: "SampleTaskMethods", task: TaskMethod):
        a, kw, mock = self.args, self.kwargs, obj.mock
        for res in [task.apply_async(a, kw), task.s(*a[2:], **kw).apply_async(a[:2])]:
            val = res.get()
            assert mock.return_value == val
        mock.assert_has_calls([call(*a, **kw)] * 2)

    def test_call(self, obj: "SampleTaskMethods", task: TaskMethod):
        a, kw, mock = self.args, self.kwargs, obj.mock
        a, kw = self.args, self.kwargs
        for val in [task(*a, **kw), task.s(*a[2:])(*a[:2], **kw)]:
            assert mock.return_value == val
        mock.assert_has_calls([call(*a, **kw)] * 2)

    @pytest.mark.parametrize("mode", ["apply", "delay"])
    def test_as_link(self, mode, obj: "SampleTaskMethods"):
        a, kw, mock = self.args, self.kwargs, obj.mock
        parent = result(a[0])
        parent.link(obj.method.s(*a[1:], **kw))
        res: AsyncResult = getattr(parent, mode)()
        mock.wait_for_call(call(*a, **kw))
        val = res.get()
        assert val == a[0]

    @pytest.mark.skipif(
        not sys.platform.startswith("linux"), reason="Only passes on linux systems"
    )
    @pytest.mark.parametrize("mode", ["apply", "delay"])
    def test_as_link_error(self, mode, obj: "SampleTaskMethods"):
        a, kw, mock = self.args, self.kwargs, obj.mock
        error, task_id = TestError(), uuid4()

        parent = result(error).set(task_id=task_id)

        parent.link_error(obj.method.s(*a, **kw))
        res: AsyncResult = getattr(parent, mode)()
        with pytest.raises(TestError):
            res.get()
        req = AnyThing(lambda v: v.id == task_id, spec=Context)
        mock.wait_for_call(call(req, error, res.traceback, *a, **kw))

    @pytest.mark.parametrize("mode", ["apply", "delay"])
    def test_with_chain(self, mode, obj: "SampleTaskMethods"):
        a, kw, mock = self.args, self.kwargs, obj.mock
        sig = wrap.s(str) | obj.method.si(*a, **kw)
        res: AsyncResult = getattr(sig, mode)()
        val = res.get(timeout=8)
        mock.wait_for_call(call(*a, **kw))
        assert val == mock.return_value
        # assert 0

    @pytest.mark.parametrize("mode", ["apply", "delay"])
    def test_with_group(self, mode, obj: "SampleTaskMethods"):
        a, kw, mock = self.args, self.kwargs, obj.mock
        sig = group([result(a[0]), obj.method.s(*a, **kw)])
        res: AsyncResult = getattr(sig, mode)()
        val = res.get(timeout=8)
        mock.wait_for_call(call(*a, **kw))
        assert val == [a[0], mock.return_value]
        # assert 0
