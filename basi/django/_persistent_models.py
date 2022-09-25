import typing as t 

from django.db import models 
from django.apps import apps 


from basi import SupportsPersistentPickle





def load_persisted(app_label, model_name, pk, using=None, /):
    cls: type[models.Model] = apps.get_model(app_label, model_name)
    qs = cls._default_manager.using(using)
    return qs.filter(pk=pk).first()

load_persisted.__safe_for_unpickle__ = True



    
def _patch_base():
    SupportsPersistentPickle.register(models.Model)
    def __reduce_persistent__(self: models.Model):
        if self.pk:
            meta = self._meta
            return load_persisted, (meta.app_label, meta.model_name, self.pk, self._state.db)

        return NotImplemented
    models.Model.__reduce_persistent__ = __reduce_persistent__
    


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
    


    