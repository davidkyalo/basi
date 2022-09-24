from copy import copy, deepcopy
from dataclasses import dataclass,field
import pickle
import pytest


from basi.serializers.persistent_pickle import dumps, loads, PersistentPickler



xfail = pytest.mark.xfail
parametrize = pytest.mark.parametrize


@dataclass
class Normal:
    foo: str
    bar: int
    persistent: bool = field(compare=False, default=None)


@dataclass
class Persistent(Normal):

    @classmethod
    def load_persistent(cls, state: dict):
        self = cls.__new__(cls)
        self.__dict__.update(state)
        self.persistent = True
        return self

    def __reduce_persistent__(self):
        return self.load_persistent, (self.__dict__.copy(),),



class PersistentPickleTests:

    def test_normal(self):
        n = Normal('one', 1)
        print(repr(n))
        assert loads(dumps(n)) == n
        
    def test_persistent(self):
        n = Persistent('one', 1)
        l = loads(dumps(n))
        print(repr(n), repr(l), sep='\n')
        assert not n.persistent  
        assert l.persistent  
        assert l == n