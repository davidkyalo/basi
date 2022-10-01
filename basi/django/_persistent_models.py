from copy import copy
from functools import wraps
import typing as t 

from django.db import models 
from django.apps import apps 
from celery.local import PromiseProxy, Proxy

from basi import SupportsPersistentPickle





def load_persisted(app_label, model_name, pk, using=None, /):
    cls: type[models.Model] = apps.get_model(app_label, model_name)
    qs = cls._default_manager.using(using)
    return PromiseProxy(lambda: qs.get(pk=pk))

load_persisted.__safe_for_unpickle__ = True


def load_queryset(cls: type[models.QuerySet], state: dict):
    qs = cls()
    qs.__setstate__(state)
    return qs

load_queryset.__safe_for_unpickle__ = True



    
def _patch_base():
    SupportsPersistentPickle.register(models.Manager)
    SupportsPersistentPickle.register(models.QuerySet)

    @wraps(SupportsPersistentPickle.__reduce_persistent__)
    def _reduce_query_(self: models.QuerySet):
        q: models.QuerySet = copy(self)
        q._result_cache = []
        q._prefetch_done = True
        state = q.__getstate__() | { '_result_cache': None, '_prefetch_done': False }
        return load_queryset, (q.__class__, state),

    models.QuerySet.__reduce_persistent__ = _reduce_query_


    SupportsPersistentPickle.register(models.Model)
    @wraps(SupportsPersistentPickle.__reduce_persistent__)
    def _reduce_model_(self: models.Model):
        if self.pk:
            meta = self._meta
            return load_persisted, (meta.app_label, meta.model_name, self.pk, self._state.db)
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
            if ctype := getattr(self, 'polymorphic_ctype', None):
                model = ctype.app_label, ctype.model
            else:
                meta = self._meta
                model = meta.app_label, meta.model_name
            return load_persisted, (*model, self.pk, self._state.db)
        return NotImplemented

    PolymorphicModel.__reduce_persistent__ = __reduce_persistent__
    


    