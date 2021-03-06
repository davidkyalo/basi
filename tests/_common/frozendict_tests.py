import pytest


from basi._common import FrozenDict, ReadonlyDict


xfail = pytest.mark.xfail
parametrize = pytest.mark.parametrize


class FrozenDictTests:
    def test_basic(self):
        vals = dict(a=1, b=2, c=3)
        dct = FrozenDict(vals)
        assert isinstance(dct, FrozenDict)
        assert isinstance(dct, ReadonlyDict)
        assert dct == vals == FrozenDict(**vals)
        assert {dct: vals}[FrozenDict(vals)] is vals
        rev = [*vals.items()][::-1]
        assert dct == FrozenDict(rev) == FrozenDict(rev[::-1])
        assert hash(dct) == hash(FrozenDict(rev))

    @xfail(raises=TypeError, strict=True)
    def test_xfail_not_hashable(self):
        vals = dict(a=1, b={}, c=[])
        dct = FrozenDict(vals)
        {dct: vals}[dct]
