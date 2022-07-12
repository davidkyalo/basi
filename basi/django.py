from collections import defaultdict
import os
from django import setup as dj_setup
from django.apps import apps
from django.conf import settings

from . import Bus, APP_CLASS_ENVVAR

SETTINGS_NAMESPACE = 'CELERY'
TASKS_MODULE = 'tasks'


def get_default_app(*, setup: bool=True, set_prefix=False):
    setup and dj_setup(set_prefix=set_prefix)
    from . import get_current_app
    return get_current_app()
    

def gen_app_task_name(bus: Bus, name, module: str):
    if app := apps.get_containing_app_config(module):
        module = app.label
    return f'{module}.{name}'


def _set_default_settings(namespace=SETTINGS_NAMESPACE):
    defaults = {
        'app_class': os.getenv(APP_CLASS_ENVVAR),
        'task_name_generator': gen_app_task_name,
    }

    prefix = namespace and f'{namespace}_' or ''
    for k, v in defaults.items():
        n = f'{prefix}{k}'.upper()
        if (s := getattr(settings, n, None)) is None:
            setattr(settings, n, s := v)
        if k == 'app_class':
            os.environ[APP_CLASS_ENVVAR] = s

        


def configure(bus: Bus, namespace=SETTINGS_NAMESPACE):
    _set_default_settings(namespace)
    bus.config_from_object(settings, namespace=namespace)



def autodiscover_app_tasks(bus: Bus):
    mods = defaultdict(list)
    for a in apps.get_app_configs():
        mods[getattr(a, 'tasks_module', None) or TASKS_MODULE].append(a.name)
    
    for m, p in mods.items():
        bus.autodiscover_tasks(p, m)


    
