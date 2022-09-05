from collections import defaultdict
import os
from django import setup as dj_setup
from django.apps import apps
from django.conf import settings

from .. import Bus, APP_CLASS_ENVVAR, get_current_app

TASKS_MODULE = 'tasks'


def get_default_app(*, setup: bool=True, set_prefix=False)-> Bus:
    setup and dj_setup(set_prefix=set_prefix)
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
        'task_name_generator': gen_app_task_name,
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


    
