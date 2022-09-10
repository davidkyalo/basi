from collections import abc, defaultdict
from functools import wraps
import os
from typing import TYPE_CHECKING, Any, TypeVar
from typing_extensions import Self
from django import setup as dj_setup
from django.apps import apps
from django.conf import settings
from celery import shared_task, Task as BaseTask
from celery.canvas import Signature

from .. import Bus, APP_CLASS_ENVVAR, get_current_app, Task

if TYPE_CHECKING:
    from django.db.models import Model


TASKS_MODULE = 'tasks'


def get_default_app(*, setup: bool | abc.Callable=True, set_prefix=False)-> Bus:
    if setup is True:
        setup = dj_setup
    setup and setup(set_prefix=set_prefix)
    return get_current_app()
    

def gen_app_task_name(bus: Bus, name, module: str):
    if app := apps.get_containing_app_config(module):
        module = module[len(app.name):].lstrip('.')
        prefix = f"{getattr(app, 'tasks_module', None) or TASKS_MODULE}"
        if module == prefix:
            module = app.label
        elif module.startswith(prefix + '.'):
            module = f"{app.label}{module[len(prefix):]}"
        else:
            module = f"{app.label}.{module}".rstrip('.')
    return f'{module}.{name}'


def _init_settings(namespace):
    defaults = {
        'app_class': os.getenv(APP_CLASS_ENVVAR),
    }
    
    prefix = namespace and f'{namespace}_' or ''
    for k, v in defaults.items():
        n = f'{prefix}{k}'.upper()
        if (s := getattr(settings, n, None)) is None:
            setattr(settings, n, s := v)
        elif k == 'app_class':
            os.environ[APP_CLASS_ENVVAR] = s


        


def autodiscover_app_tasks(bus: Bus, module=TASKS_MODULE):
    mods = defaultdict(list)
    for a in apps.get_app_configs():
        mods[getattr(a, 'tasks_module', None) or module].append(a.name)
    
    for m, p in mods.items():
        bus.autodiscover_tasks(p, m)


    


_T_Model = TypeVar('_T_Model', bound='Model')





def bind_model(func=None, /, model: type=None):
    def decorator(fn):
        from django.db.models import Model
        @wraps(fn)
        def run(self: Task, /, *a, **kw):
            if isinstance(self, BaseTask):
                self, *a = [a[0], self, *a[1:]]
            
            cls = model or Model
            if not isinstance(self, cls):
                if isinstance(self, (list, tuple)):
                    *mn, pk = self
                    cls = apps.get_model(*mn)
                    assert not model or issubclass(cls, model)
                else:
                    pk = self
                self = cls._default_manager.get(pk=pk)
            
            return fn(self, *a, **kw)
        
        return run

    return decorator if func is None else decorator(func)


    
    
class model_task_method:
    func: abc.Callable = None
    options: dict[str, Any] = None
    pk_field: str = 'pk'
    attr_name = None
    task = None
    model = None
    task: Task
    attr: str

    def __init__(self, func=None, /, attr_name: str=None, **options) -> None:
        if isinstance(func, BaseTask):
            self.task = func
        else:
            self.func, self.attr_name, self.options = func, attr_name, options
    
    def __call__(self, func) -> Self:
        self.func = func
        return self

    def __get__(self, obj: _T_Model, typ: type[_T_Model]=None) -> Signature:
        if obj is None:
            return self.task
        if not (pk := getattr(obj, self.pk_field, None)) is None:
            meta = obj._meta
            return self.task.signature([[meta.app_label, meta.object_name, pk]])
        raise AttributeError(self.task.name)

    def _register_task(self, cls: type[_T_Model], name: str):
        if self.task:
            raise TypeError('task already set')
        func = bind_model(self.func, cls)
        func.__name__ = name = self.attr_name or name
        self.task = shared_task(func, **{'name': f'{cls.__module__}.{cls.__qualname__}.{name}'} | self.options)

    def contribute_to_class(self, cls, name):
        assert self.func or self.task
        self.task or self._register_task(cls, name)
        setattr(cls, self.attr_name or name, self)

