

from ast import arg
from collections import abc
from typing import TypeVar


from typing_extensions import ParamSpec, Self

from celery.canvas import Signature, chain
from basi import shared_task, Task

from celery.contrib.testing import tasks as _

_P = ParamSpec('_P')
_R = TypeVar('_R')
_T = TypeVar('_T')



def _apply_async(self, *a, **kw):
    return self.apply(*a, **kw)



del _apply_async


