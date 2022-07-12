from types import ModuleType
from typing import Optional
from django.apps import AppConfig

from .django import configure, autodiscover_app_tasks

from . import get_current_app




class BasiConfig(AppConfig):

    name = f'{__package__}'
    tasks_module: Optional[str]

    def __init__(self, app_name: str, app_module: Optional[ModuleType]) -> None:
        super().__init__(app_name, app_module)
        configure(get_current_app())

    def ready(self) -> None:
        autodiscover_app_tasks(get_current_app())