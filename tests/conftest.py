import asyncio
from contextlib import suppress
from inspect import isfunction
import sys
from weakref import ref

import pytest
import typing as t

import builtins
from basi.testing import TestError


def _pp(*lines, label=None, **kw):
    from pprint import pformat

    fr = None
    with suppress(BaseException):
        fr = sys._getframe(1)
    kw.setdefault("sort_dicts", False)
    kw.setdefault("indent", 2)
    kw.setdefault("depth", 8)
    ln = 100
    if not label:
        with suppress(BaseException):
            label = fr.f_globals["__name__"]
            label = f"{label}::{getattr(fr.f_code, 'co_qualname',fr.f_code.co_name)}"

    print("")
    print("-" * 120)
    print(f"{f' {label} ':-^120}")

    for ln in lines or [getattr(fr, "f_locals", "")]:
        print(" ", pformat(ln, **kw).replace("\n", "\n  "))
    print("-" * 120)
    with suppress(BaseException):
        print(f"{f' {fr.f_code.co_filename}:{fr.f_lineno} ':<120}")
    print("=" * 120)


builtins.pp = _pp


@pytest.fixture
def new_args():
    return ()


@pytest.fixture
def new_kwargs():
    return {}


@pytest.fixture
def new(cls, new_args, new_kwargs):
    return lambda *a, **kw: cls(*a, *new_args[len(a) :], **{**new_kwargs, **kw})


@pytest.fixture
def immutable_attrs(cls):
    return [a for a in dir(cls) if not (a[:2] == "__" == a[-2:] or isfunction(getattr(cls, a)))]


_exc_ = 0


@pytest.fixture()
def exception(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    global _exc_
    _exc_ += 1
    cls = type(
        f"{request.node.name}[exception-{_exc_:03}]",
        (TestError,),
        {"__module__": request.module.__name__, "request": ref(request)},
    )

    monkeypatch.setattr(request.module, cls.__name__, cls, raising=False)
    yield cls


@pytest.fixture(scope="session")
def celery_enable_logging():
    return True


@pytest.fixture(autouse=True, scope="session")
def celery_includes(celery_includes):
    return [
        *celery_includes,
        f"{__package__}.tasks",
    ]


@pytest.fixture(scope="session")
def celery_config(celery_config):
    # type: (...) -> dict[str, t.Any]
    """Redefine this fixture to configure the test Celery app.

    The config returned by your fixture will then be used
    to configure the :func:`celery_app` fixture.
    """

    return {
        **celery_config,
        "event_serializer": "pickle",
        "result_serializer": "pickle",
        "task_serializer": "pickle",
        "accept_content": ["application/json", "application/x-python-serialize"],
        "task_annotations": {"*": {"trace": True}},
    }
