from copy import copy, deepcopy
import pickle
import pytest


from basi._common import Missing, MissingType


xfail = pytest.mark.xfail
parametrize = pytest.mark.parametrize


class test_MissingType:
    def test_basic(self):
        assert not Missing
        assert isinstance(Missing, MissingType)
        assert Missing == MissingType()
        assert Missing != None

    def test_copy(self):
        cp = copy(Missing)
        assert cp == Missing
        assert cp is Missing

    def test_deepcopy(self):
        cp = deepcopy(Missing)
        assert cp == Missing
        assert cp is Missing

    def test_pickle(self):
        pk = pickle.dumps(Missing)
        cp = pickle.loads(pk)
        assert cp == Missing
        assert cp is Missing
