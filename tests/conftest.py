import asyncio
from inspect import isfunction
import pytest
import typing as t


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
    return [
        a
        for a in dir(cls)
        if not (a[:2] == "__" == a[-2:] or isfunction(getattr(cls, a)))
    ]


