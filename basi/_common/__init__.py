from collections import Counter, abc, defaultdict
from functools import partial
import inspect
import re
import sys
from threading import Lock
import typing as t
from collections.abc import Callable, Hashable
from copy import deepcopy
from importlib import import_module

from typing_extensions import Self

_object_setattr = object.__setattr__
_setattr = setattr

_T = t.TypeVar("_T")





def cached_import(module_path, qualname: str):
    modules = sys.modules
    if module_path not in modules or (
        # Module is not fully initialized.
        getattr(modules[module_path], "__spec__", None) is not None
        and getattr(modules[module_path].__spec__, "_initializing", False) is True
    ):
        import_module(module_path)
    
    obj = modules[module_path]
    for attr in qualname.split('.'):
        obj = getattr(obj, attr)
    return obj


def import_string(path: str):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    path: str
    try:
        module, qualname = path.rsplit(':' if ':' in path else '.', 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % path) from err

    try:
        return cached_import(module, qualname)
    except AttributeError as err:
        raise ImportError(
            'Module "%s" does not define a "%s" attribute/class'
            % (module, qualname)
        ) from err


__uid_lock = Lock()
__uids = Counter()
def unique_id(nspace: t.Any=None):
    global __uid_lock, __uids
    with __uid_lock:
        __uids[nspace] += 1
        return __uids[nspace]
        

def ordered_set(it: abc.Iterable[_T]) -> abc.Set[_T]:
    return dict.fromkeys(it).keys()


_dunder_re = re.compile(r'^__([^_].*[^_])__$')
def _strip_dunder(name: str):
    """
    Returns True if a __dunder__ name, False otherwise.
    """
    global _dunder_re
    if _dunder_re.search(name):
        return name[2:-2]



_sunder_re = re.compile(r'^_([^_].*[^_])_$')
def _strip_sunder(name: str):
    """
    Returns True if a _sunder_ name, False otherwise.
    """
    global _sunder_re
    if _sunder_re.search(name):
        return name[1:-1]


_protected_re = re.compile(r'^_([^_].*)$')
def _strip_protected(name: str):
    """
    Returns True if a _protected name, False otherwise.
    """
    global _protected_re
    if _protected_re.search(name):
        return name[1:]



def _strip_private(name: str, *classes: t.Union[type,str]):
    for cls_name in (classes or (_strip_protected(name) or '').partition('__')[:1]):
        pattern = getattr(cls_name, '__private_attrs_regex__', None) \
            or _private_attr_regex(cls_name)
        if match := pattern.search(name):
            return match.group(1)
            


def _private_attr_regex(*classes: t.Union[type,str]):
    skip = set()
    pre = r"|".join(
            n for c in classes 
                for n in ((c if isinstance(c, str) else c.__name__).lstrip("_"),)
                    if not (n in skip or skip.add(n))
    )

    return re.compile(fr"^_(?:{pre})__(.+(?<!_)_?)$")


def _make_private(klass: t.Union[type,str], name: str):
    return f'_{(klass if isinstance(klass, str) else klass.__name__).lstrip("_")}__{name}'


def private_setattr(
    klass=None,
    *,
    name: str = "setattr",
    setattr=True,
    setattr_fn=_object_setattr,
    ignore: t.Union[abc.Callable, abc.Sequence[str]]=None,
    frozen: str = None,
    freeze_private: bool=None,
):
    if freeze_private is None:
        freeze_private = not not frozen

    if not ignore:
        def can_setattr(self, n: str):
            nonlocal freeze_private, frozen
            return (_strip_private(n, self.__class__) and not (freeze_private and getattr(self, frozen, False)))
    elif isinstance(ignore, abc.Sequence):
        ignore = {*ignore}
        def can_setattr(self, n: str):
            nonlocal ignore, freeze_private, frozen
            return n in ignore or (_strip_private(name, self.__class__) and not (freeze_private and getattr(self, frozen, False)))
    else:
        def can_setattr(self, n: str):
            nonlocal ignore, freeze_private, frozen
            return ignore(n) or (_strip_private(n, self.__class__) and not (freeze_private and getattr(self, frozen, False)))
    
    def _set_private_setattr(cls):
        if not hasattr(cls, fname := _make_private(cls, name)):
            fn = setter
            for b in cls.__bases__:
                if fn := getattr(b, _make_private(b, name), None):
                    break
            type.__setattr__(cls, fname, fn or setter)
            

    def setter(self: Self, name=None, value=None, force=False, /, **kw):
        if not force and frozen and getattr(self, frozen, False):
            setter_ = _setattr
        else:
            setter_ = setattr_fn

        name and kw.setdefault(name, value)
        for k, v in kw.items():
            setter_(self, k, v)

    def __setattr__(self: Self, name: str, value):
        if can_setattr(self, name):
            return setattr_fn(self, name, value)

        getattr(self, name)
        raise AttributeError(
            f"`cannot set {name!r} on frozen {self.__class__.__qualname__!r}."
        )

    def decorator(cls_):
        nonlocal frozen
        if frozen and frozen[0] == '_' and _strip_protected(frozen[1:]):
            frozen = _make_private(cls_, frozen[2:])

        _base__init_subclass__ = cls_.__init_subclass__

        def __init_subclass__(cls: type[Self], **kwargs):
            _set_private_setattr(cls)
            type.__setattr__(cls, '__private_attrs_regex__', _private_attr_regex(*cls.__mro__))
            _base__init_subclass__(**kwargs)

        type.__setattr__(cls_, '__init_subclass__', classmethod(__init_subclass__))
        type.__setattr__(cls_, '__private_attrs_regex__', _private_attr_regex(*cls_.__mro__))

        _set_private_setattr(cls_)

        if setattr:
            if cls_.__setattr__ is _object_setattr or cls_.__setattr__.__qualname__ != __setattr__.__qualname__:
                type.__setattr__(cls_, '__setattr__', __setattr__)

        return cls_

    return decorator if klass is None else decorator(klass)


def typed_signature(
    callable: Callable[..., t.Any], *, follow_wrapped=True, globalns=None, localns=None
) -> inspect.Signature:
    sig = inspect.signature(callable, follow_wrapped=follow_wrapped)

    if follow_wrapped:
        callable = inspect.unwrap(
            callable, stop=(lambda f: hasattr(f, "__signature__"))
        )

    if globalns is None:
        if not (globalns := getattr(callable, "__globals__", None)):
            if isinstance(callable, partial):
                callable = callable.func
            getattr(import_module(callable.__module__), "__dict__", None)

    params = (
        p.replace(annotation=eval_type(p.annotation, globalns, localns))
        for p in sig.parameters.values()
    )

    return sig.replace(
        parameters=params,
        return_annotation=eval_type(sig.return_annotation, globalns, localns),
    )


def eval_type(value, globalns, localns=None):

    if isinstance(value, str):
        value = t.ForwardRef(value)
    try:
        return t._eval_type(value, globalns, localns)
    except NameError:  # pragma: no cover
        return value


class MissingType:

    __slots__ = ()

    __value__: t.ClassVar["MissingType"] = None

    def __new__(cls):
        return cls.__value__

    @classmethod
    def _makenew__(cls, name):
        if cls.__value__ is None:
            cls.__value__ = object.__new__(cls)
        return cls()

    def __bool__(self):
        return False

    def __str__(self):
        return ""

    def __repr__(self):
        return f"Missing"

    def __reduce__(self):
        return self.__class__, ()  # pragma: no cover

    def __eq__(self, x):
        return x is self

    def __hash__(self):
        return id(self)


Missing = MissingType._makenew__("Missing")


_T_Key = t.TypeVar("_T_Key")
_T_Val = t.TypeVar("_T_Val", covariant=True)
_T_Default = t.TypeVar("_T_Default", covariant=True)


class ReadonlyDict(dict[_T_Key, _T_Val]):
    """A readonly `dict` subclass.

    Raises:
        TypeError: on any attempted modification
    """

    __slots__ = ()

    def not_mutable(self, *a, **kw):
        raise TypeError(f"readonly type: {self} ")

    __delitem__ = __setitem__ = setdefault = not_mutable
    clear = pop = popitem = update = __ior__ = not_mutable
    del not_mutable

    @classmethod
    def fromkeys(cls, it: abc.Iterable[_T_Key], value: _T_Val = None):
        return cls((k, value) for k in it)

    def __reduce__(self):
        return (
            self.__class__,
            (dict(self),),
        )

    def copy(self):
        return self.__class__(self)

    __copy__ = copy

    def __deepcopy__(self, memo=None):
        return self.__class__(deepcopy(dict(self), memo))

    __or = dict[_T_Key, _T_Val].__or__

    def __or__(self, o):
        return self.__class__(self.__or(o))


class FrozenDict(ReadonlyDict[_T_Key, _T_Val]):
    """An hashable `ReadonlyDict`"""

    __slots__ = ("_v_hash",)

    def __hash__(self):
        try:
            ash = self._v_hash
        except AttributeError:
            ash = None
            items = self._eval_hashable()
            if items is not None:
                try:
                    ash = hash(items)
                except TypeError:
                    pass
            _object_setattr(self, "_v_hash", ash)

        if ash is None:
            raise TypeError(f"un-hashable type: {self.__class__.__name__!r}")

        return ash

    def _eval_hashable(self) -> Hashable:
        return (*((k, self[k]) for k in sorted(self)),)
