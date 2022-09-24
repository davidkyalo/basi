
from abc import ABC, abstractmethod
from collections import abc
import io
import typing as t 
import pickle

from kombu import serialization



class SupportsPersistentPickle(ABC):

    @abstractmethod
    def __reduce_persistent__(self):
        return NotImplemented

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is SupportsPersistentPickle:
            return callable(getattr(subclass, '__reduce_persistent__', None))
        return NotImplemented




def _not_implemented():
    return NotImplemented




class PersistentPickler(pickle.Pickler):

    def reducer_override(self, obj):
        if isinstance(obj, SupportsPersistentPickle):
            return getattr(obj, '__reduce_persistent__', _not_implemented)()
        return NotImplemented


def dumps(obj):
    fo = io.BytesIO()
    PersistentPickler(fo).dump(obj)
    return fo.getvalue()

def loads(obj):
    return pickle.loads(obj)




serialization.register(
    'persistent_pickle', dumps, loads,
    content_type='application/persistent-pickle',
    content_encoding='binary',
)

