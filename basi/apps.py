import os
from types import ModuleType
from typing import Optional
from django.apps import AppConfig
from .django import _init_settings, autodiscover_app_tasks

from . import get_current_app, SETTINGS_ENVVAR, DEFAULT_NAMESPACE


os.environ.setdefault(SETTINGS_ENVVAR, 'django.conf:settings')


class BasiConfig(AppConfig):

    name = f'{__package__}'
    tasks_module: Optional[str]

    def __init__(self, app_name: str, app_module: Optional[ModuleType]) -> None:
        super().__init__(app_name, app_module)
        _init_settings(DEFAULT_NAMESPACE)
        from .django._persistent_models import _patch_base
        _patch_base()

    def import_models(self) -> None:
        from .django._persistent_models import _patch_polymorphic
        _patch_polymorphic()
        return super().import_models()

    def ready(self) -> None:
        autodiscover_app_tasks(get_current_app())