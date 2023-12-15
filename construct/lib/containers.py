from construct.lib.py3compat import *
import re
import sys


globalPrintFullStrings = False
globalPrintFalseFlags = False
globalPrintPrivateEntries = False


def setGlobalPrintFullStrings(enabled=False):
    r"""
    When enabled, Container __str__ produces full content of bytes and unicode strings, otherwise and by default, it produces truncated output (16 bytes and 32 characters).

    :param enabled: bool
    """
    global globalPrintFullStrings
    globalPrintFullStrings = enabled


def setGlobalPrintFalseFlags(enabled=False):
    r"""
    When enabled, Container __str__ that was produced by FlagsEnum parsing prints all values, otherwise and by default, it prints only the values that are True.

    :param enabled: bool
    """
    global globalPrintFalseFlags
    globalPrintFalseFlags = enabled


def setGlobalPrintPrivateEntries(enabled=False):
    r"""
    When enabled, Container __str__ shows keys like _ _index _etc, otherwise and by default, it hides those keys. __repr__ never shows private entries.

    :param enabled: bool
    """
    global globalPrintPrivateEntries
    globalPrintPrivateEntries = enabled


def recursion_lock(retval="<recursion detected>", lock_name="__recursion_lock__"):
    """Used internally."""
    def decorator(func):
        def wrapper(self, *args, **kw):
            if getattr(self, lock_name, False):
                return retval
            setattr(self, lock_name, True)
            try:
                return func(self, *args, **kw)
            finally:
                delattr(self, lock_name)

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


class Container(dict):
    # NOTE: be careful when working with these objects. Any method can be shadowed, so instead of doing `self.items()` you should do `dict.items(self)`. Operation that use methods implicitly (such as `x in self` or `self[k]`) will work as usual.
    r"""
    Generic ordered dictionary that allows both key and attribute access, and preserves key order by insertion. Adding keys is preferred using \*\*entrieskw. Equality does NOT check item order. Also provides regex searching.

    Example::

        >>> Container()
        >>> Container([("name", "anonymous"), ("age", 21)])
        >>> Container(name="anonymous", age=21)
        >>> Container(dict2)
        >>> Container(container2)

    ::

        >>> print(repr(obj))
        Container(text='utf8 decoded string...', value=123)
        >>> print(obj)
        Container
            text = u'utf8 decoded string...' (total 22)
            value = 123
    """
    __slots__ = ('__dict__', '__recursion_lock__')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def copy(self, /):
        return self.__class__(self)

    def __copy__(self, /):
        return self.__class__.copy(self)

    # this is required because otherwise copy.deepcopy() will
    # copy self and self.__dict__ separately for some reason
    def __deepcopy__(self, _, /):
        return self.__class__.copy(self)

    def __dir__(self, /):
        """For auto completion of attributes based on container values."""
        return list(self.__class__.keys(self)) + list(self.__class__.__dict__) + dir(super(Container, self))

    def __eq__(self, other, /):
        if self is other:
            return True
        if not isinstance(other, dict):
            return False
        def isequal(v1, v2):
            if v1.__class__.__name__ == "ndarray" or v2.__class__.__name__ == "ndarray":
                import numpy
                return numpy.array_equal(v1, v2)
            return v1 == v2
        for k, v in self.__class__.items(self):
            if isinstance(k, unicodestringtype) and k.startswith(u"_"):
                continue
            if isinstance(k, bytestringtype) and k.startswith(b"_"):
                continue
            if k not in other or not isequal(v, other[k]):
                return False
        for k, v in other.__class__.items(other):
            if isinstance(k, unicodestringtype) and k.startswith(u"_"):
                continue
            if isinstance(k, bytestringtype) and k.startswith(b"_"):
                continue
            if k not in self or not isequal(v, self[k]):
                return False
        return True

    def __ne__(self, other, /):
        return not self == other

    @recursion_lock()
    def __repr__(self, /):
        parts = []
        for k, v in self.__class__.items(self):
            if isinstance(k, str) and k.startswith("_"):
                continue
            if isinstance(v, stringtypes):
                parts.append(str(k) + "=" + reprstring(v))
            else:
                parts.append(str(k) + "=" + repr(v))
        return "Container(%s)" % ", ".join(parts)

    @recursion_lock()
    def __str__(self, /):
        indentation = "\n    "
        text = ["Container: "]
        isflags = getattr(self, "_flagsenum", False)
        for k, v in self.__class__.items(self):
            if isinstance(k, str) and k.startswith("_") and not globalPrintPrivateEntries:
                continue
            if isflags and not v and not globalPrintFalseFlags:
                continue
            text.extend([indentation, str(k), " = "])
            if v.__class__.__name__ == "EnumInteger":
                text.append("(enum) (unknown) %s" % (v, ))
            elif v.__class__.__name__ == "EnumIntegerString":
                text.append("(enum) %s %s" % (v, v.intvalue, ))
            elif v.__class__.__name__ in ["HexDisplayedBytes", "HexDumpDisplayedBytes"]:
                text.append(indentation.join(str(v).split("\n")))
            elif isinstance(v, bytestringtype):
                printingcap = 16
                if len(v) <= printingcap or globalPrintFullStrings:
                    text.append("%s (total %d)" % (reprstring(v), len(v)))
                else:
                    text.append("%s... (truncated, total %d)" % (reprstring(v[:printingcap]), len(v)))
            elif isinstance(v, unicodestringtype):
                printingcap = 32
                if len(v) <= printingcap or globalPrintFullStrings:
                    text.append("%s (total %d)" % (reprstring(v), len(v)))
                else:
                    text.append("%s... (truncated, total %d)" % (reprstring(v[:printingcap]), len(v)))
            else:
                text.append(indentation.join(str(v).split("\n")))
        return "".join(text)

    def _search(self, compiled_pattern, search_all, /):
        items = []
        for key, value in self.__class__.items(self):
            try:
                if isinstance(value, (Container, ListContainer)):
                    ret = value.__class__._search(value, compiled_pattern, search_all)
                    if ret is not None:
                        if search_all:
                            items.extend(ret)
                        else:
                            return ret
                elif compiled_pattern.match(key):
                    if search_all:
                        items.append(value)
                    else:
                        return value
            except Exception:
                pass
        if search_all:
            return items
        else:
            return None

    def search(self, pattern):
        """
        Searches a container (non-recursively) using regex.
        """
        compiled_pattern = re.compile(pattern)
        return self.__class__._search(self, compiled_pattern, False)

    def search_all(self, pattern):
        """
        Searches a container (recursively) using regex.
        """
        compiled_pattern = re.compile(pattern)
        return self.__class__._search(self, compiled_pattern, True)

    def __getstate__(self, /):
        """
        Used by pickle to serialize an instance to a dict.
        """
        return dict(self)

    def __setstate__(self, state, /):
        """
        Used by pickle to de-serialize from a dict.
        """
        self.__class__.clear(self)
        self.__class__.update(self, state)


class ListContainer(list):
    r"""
    Generic container like list. Provides pretty-printing. Also provides regex searching.

    Example::

        >>> ListContainer()
        >>> ListContainer([1, 2, 3])

    ::

        >>> obj
        ListContainer([1, 2, 3])
        >>> print(repr(obj))
        ListContainer([1, 2, 3])
        >>> print(obj)
        ListContainer
            1
            2
            3
    """

    @recursion_lock()
    def __repr__(self, /):
        return "ListContainer(%s)" % (list.__repr__(self),)

    @recursion_lock()
    def __str__(self, /):
        indentation = "\n    "
        text = ["ListContainer: "]
        for k in self:
            text.append(indentation)
            lines = str(k).split("\n")
            text.append(indentation.join(lines))
        return "".join(text)

    def _search(self, compiled_pattern, search_all, /):
        items = []
        for item in self:
            try:
                ret = item.__class__._search(item, compiled_pattern, search_all)
            except Exception:
                continue
            if ret is not None:
                if search_all:
                    items.extend(ret)
                else:
                    return ret
        if search_all:
            return items
        else:
            return None

    def search(self, pattern):
        """
        Searches a container (non-recursively) using regex.
        """
        compiled_pattern = re.compile(pattern)
        return self._search(compiled_pattern, False)

    def search_all(self, pattern):
        """
        Searches a container (recursively) using regex.
        """
        compiled_pattern = re.compile(pattern)
        return self._search(compiled_pattern, True)
