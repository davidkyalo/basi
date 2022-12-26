import typing as t
from copy import copy
from functools import wraps

from celery.local import PromiseProxy, Proxy
from django.apps import apps
from django.db import models

from basi import SupportsPersistentPickle


def load_persisted(model, pk, using=None, /):
    return PromiseProxy(lambda: apps.get_model(model)._default_manager.using(using).get(pk=pk))


load_persisted.__safe_for_unpickle__ = True


def _patch_base():
    SupportsPersistentPickle.register(models.Model)

    @wraps(SupportsPersistentPickle.__reduce_persistent__)
    def _reduce_model_(self: models.Model):
        if self.pk:
            return load_persisted, (self._meta.label_lower, self.pk, self._state.db)
        return NotImplemented

    models.Model.__reduce_persistent__ = _reduce_model_


def _patch_polymorphic():
    PolymorphicModel: type[models.Model]
    try:
        from polymorphic.models import PolymorphicModel
    except ImportError:
        return

    def __reduce_persistent__(self: models.Model):
        if self.pk:
            model = self.__class__
            if getattr(self, "polymorphic_ctype", None):
                model = self.get_real_instance_class()
            return load_persisted, (model._meta.label_lower, self.pk, self._state.db)
        return NotImplemented

    PolymorphicModel.__reduce_persistent__ = __reduce_persistent__
