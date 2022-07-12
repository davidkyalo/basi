import os

from celery import current_task
from celery.local import Proxy
from .base import Bus, Task, Celery
from ._common import import_string

current_task: Task




APP_CLASS_ENVVAR = 'CELERY_APP_CLASS'



def get_current_app():
    from celery import _state
    if app := _state.default_app:
        return app

    cls: type[Bus] = os.getenv(APP_CLASS_ENVVAR) or Bus
    if isinstance(cls, str):
        cls = import_string(cls)
    _state.set_default_app(cls(
        'default', fixups=[], set_as_current=False,
        loader=os.environ.get('CELERY_LOADER') or 'default',
    ))
    return _state.default_app




bus: Bus = Proxy(get_current_app)
app = bus