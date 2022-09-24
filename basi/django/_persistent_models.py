import typing as t 

from django.db import models 
from django.apps import apps 


from basi import SupportsPersistentPickle





def load_persisted(app_label, model_name, pk, using=None, /):
    cls: type[models.Model] = apps.get_model(app_label, model_name)
    qs = cls._default_manager.using(using)
    return qs.filter(pk).first()
    



def _patch():
    SupportsPersistentPickle.register(models.Model)
    def __reduce_persistent__(self: models.Model):
        if self.pk:
            meta = self._meta
            return load_persisted, (meta.app_label, meta.model_name, self.pk, self._state.db)

        return NotImplemented
    models.Model.__reduce_persistent__ = __reduce_persistent__
    