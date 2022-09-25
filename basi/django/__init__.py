from collections import abc, defaultdict
from functools import wraps
import os
import inspect
from types import FunctionType
from typing import TYPE_CHECKING, Any, TypeVar, Union
from typing_extensions import Self
from django import setup as dj_setup
from django.apps import apps
from django.conf import settings
from celery.local import Proxy
from celery import Task as BaseTask
from celery.canvas import Signature, signature

from .. import Bus, APP_CLASS_ENVVAR, get_current_app, Task, MethodTask, shared_method_task

if TYPE_CHECKING:
    from django.db.models import Model


TASKS_MODULE = 'tasks'


def get_default_app(*, setup: Union[bool, abc.Callable]=True, set_prefix=False)-> Bus:
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





# def _unpickle_model(model, *, cls=None):
#     from django.db.models import Model
#     res = model
#     if isinstance(model, (tuple, list)):
#         *mn, pk = model
#         res = apps.get_model(*mn)._default_manager.get(pk=pk)
#     assert isinstance(res, cls or Model), f'{res} from {model} is not {(cls or Model).__qualname__}'
#     return res

# _unpickle_model.__safe_for_unpickle__ = True


# class _ModelProxy(Proxy):
#     __slots__ = ('__object')

#     def __init__(self, local):
#         object.__setattr__(self, '_ModelProxy__object', local)

#     def _get_current_object(self):
#         return self.__object # object.__getattribute__(self, '_ModelProxy__object')

#     def __json__(self):
#         return self.__persistent_identity__()

#     def __persistent_identity__(self):
#         obj: 'Model' = self._get_current_object()
#         if not obj.pk:
#             raise ValueError(f'object not saved {obj}')
#         return obj._meta.app_label, obj._meta.object_name, obj.pk

#     def __reduce__(self):
#         return _unpickle_model, (self.__persistent_identity__(),)



# class BoundModelTask(BoundTask):
    
#     model_class: type['Model'] = None

#     def resolve_self(self, arg):
#         return _unpickle_model(arg, cls=self.model_class)


    
class model_task_method:
    func: abc.Callable = None
    options: dict[str, Any] = None
    pk_field: str = 'pk'
    attr_name = None
    task = None
    model = None
    task: MethodTask
    attr: str

    def __init__(self, func=None, /, attr_name: str=None, **options) -> None:
        from warnings import warn
        warn('`model_task_method` is deprecated in favor of `task_method`', DeprecationWarning)

        if isinstance(func, (BaseTask, Signature)):
            self.task = func
        else:
            self.func, self.attr_name, self.options = func, attr_name, options
    
    def __call__(self, func) -> Self:
        self.func = func
        return self

    def __get__(self, obj: _T_Model, typ: type[_T_Model]=None) -> Signature:
        return self.task.__get__(obj, typ).s()
        # if obj is None:
        #     return self.task
        # kwargs = {'__self__': _ModelProxy(obj)}
        # s = signature(self.task).clone(kwargs=kwargs)
        # return s

    def _register_task(self, cls: type[_T_Model], name: str):
        if self.task:
            raise TypeError('task already set')
        func = self._get_task_func(cls, name)
        self.task = shared_method_task(func, **self._get_task_options(cls, name))
        
    def _get_task_func(self, cls, name):
        func = self.func
        return func
        
    def _get_task_options(self, cls, name):
        opts = self.options
        name = opts.get("__name__") or name
        qualname = f'{cls.__qualname__}.{name}'

        return {
            'model_class': cls,
            '__qualname__': qualname,
            'typing': False,
            'name': f'{cls.__module__}.{qualname}',
        } | opts

    def contribute_to_class(self, cls, name):
        assert self.func or self.task
        self.task or self._register_task(cls, name)
        setattr(cls, self.attr_name or name, self)

