from contextlib import contextmanager
from unittest.mock import Mock, patch, create_autospec
import typing as t
from celery.worker.request import Context
from basi import current_task, Task, bus
from celery.canvas import Signature
from basi.canvas import noop, throw, run_in_worker
from basi.base import _P, _R, _T


class TaskCallMock(Mock, Task):

    mock_requests: list[Context]
    mock_request_stacks: list[list[Context]]

    if not t.TYPE_CHECKING:

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.mock_requests = []
            self.mock_request_stacks = []
    
    def s(self, *args: t.Any, **kwargs: t.Any) -> Signature[_R]:
        return super().s(*args, **kwargs)

    def si(self, *args: t.Any, **kwargs: t.Any) -> Signature[_R]:
        return super().si(*args, **kwargs)

    def _get_child_mock(self, **kw):
        ret = super()._get_child_mock(**kw)
        debug(kw, ret)
        # raise ValueError('xxxXXXxxx')
        return ret

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        self.mock_requests = self.mock_requests + [current_task.request]
        self.mock_request_stacks.append(current_task.request_stack.stack[:])
        rv = super().__call__(*args, **kwargs)
        return rv

    def reset_mock(
        self,
        visited: t.Any = None,
        *,
        return_value: bool = None,
        side_effect: bool = False
    ) -> None:
        super().reset_mock(
            visited, return_value=return_value, side_effect=side_effect
        )
        self.mock_requests = []
        self.mock_request_stacks = []



@contextmanager
def patch_task(task: t.Union[str, Task], *args, app=bus, **kwargs):
    if isinstance(task, str):
        task = app.tasks[task]
    with patch.object(task, 'run', TaskCallMock(*args, **kwargs)) as p:
        yield p


def mock_task(mock: Mock=None, signature=None):
    mock = Mock() if mock is None else mock
    