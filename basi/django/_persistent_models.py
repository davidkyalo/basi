from copy import copy
from functools import wraps
import typing as t

from django.db import models
from django.apps import apps
from celery.local import PromiseProxy, Proxy

from basi import SupportsPersistentPickle


def load_persisted(model, pk, using=None, /):
    return PromiseProxy(
        lambda: apps.get_model(model)._default_manager.using(using).get(pk=pk)
    )


load_persisted.__safe_for_unpickle__ = True




def _patch_base():
    SupportsPersistentPickle.register(models.Model)

    @wraps(SupportsPersistentPickle.__reduce_persistent__)
    def _reduce_model_(self: models.Model):
        if self.pk:
            meta = self._meta
            return load_persisted, (
                f"{meta.app_label}.{meta.model_name}",
                self.pk,
                self._state.db
            )
        return NotImplemented

    models.Model.__reduce_persistent__ = _reduce_model_


def _patch_polymorphic():
    PolymorphicModel: type[models.Model]
    try:
        from polymorphic.models import PolymorphicModel
    except ImportError:
        return

    def __reduce_persistent__(self: PolymorphicModel):
        if self.pk:
            if ctype := getattr(self, "polymorphic_ctype", None):
                model = f'{ctype.app_label}.{ctype.model}'
            else:
                meta = self._meta
                model = f'{meta.app_label}.{meta.model_name}'
            return load_persisted, (model, self.pk, self._state.db)
        return NotImplemented

    PolymorphicModel.__reduce_persistent__ = __reduce_persistent__
