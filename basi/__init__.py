from collections import abc
import os

from celery import current_task, shared_task
from celery.local import Proxy
from .base import Bus, Task, Celery
from ._common import import_string

current_task: Task

shared_task = abc.Callable[..., Task]


APP_CLASS_ENVVAR = 'CELERY_APP_CLASS'
SETTINGS_ENVVAR = 'CELERY_SETTINGS_MODULE'




def get_current_app():
    from celery import _state
    if _state.default_app:
        return _state.get_current_app()

    cls: type[Bus] = os.getenv(APP_CLASS_ENVVAR) or Bus
    if isinstance(cls, str):
        cls = import_string(cls)
    
    app = cls(
        'default', fixups=[], set_as_current=False,
        namespace=os.getenv('BASI_NAMESPACE', 'CELERY'),
        loader=os.environ.get('CELERY_LOADER') or 'default',
    )
    app.set_default()
    return _state.get_current_app()





bus: Bus = Proxy(get_current_app)
app = bus