from collections import abc
import os
from typing import TYPE_CHECKING

from celery import current_task, shared_task
from celery.local import Proxy
from .base import Bus, Task, MethodTask
from ._common import import_string
from .serializers import SupportsPersistentPickle

current_task: Task

# shared_task = abc.Callable[..., Task]


DEFAULT_NAMESPACE = os.getenv('BASI_NAMESPACE', 'CELERY')

APP_CLASS_ENVVAR = f'{DEFAULT_NAMESPACE}_APP_CLASS'
SETTINGS_ENVVAR = f'{DEFAULT_NAMESPACE}_SETTINGS_MODULE'


def get_current_app() -> Bus:
    from celery import _state
    if _state.default_app:
        return _state.get_current_app()

    cls: type[Bus] = os.getenv(APP_CLASS_ENVVAR) or Bus
    if isinstance(cls, str):
        cls = import_string(cls)
    
    app = cls(
        'default', fixups=[], set_as_current=False,
        namespace=DEFAULT_NAMESPACE,
        loader=os.environ.get('CELERY_LOADER') or 'default',
    )
    app.set_default()
    app.config_from_envvar(SETTINGS_ENVVAR)
    return _state.get_current_app()


def shared_method_task(fn=None, /, *args, base=MethodTask, **options):
    options['base'] = base or MethodTask
    def decorator(func):
        return shared_task(func, *args, **{'name': f'{func.__module__}.{func.__qualname__}'} | options)
    return decorator if fn is None else decorator(fn)

if TYPE_CHECKING:
    shared_method_task = shared_task

bus: Bus = Proxy(get_current_app)
app = bus