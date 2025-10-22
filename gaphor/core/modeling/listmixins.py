"""This module contains some support code for queries on lists.

Two mixin classes are provided:

1. ``querymixin``
2. ``recursemixin``

See the documentation on the mixins.
"""

from __future__ import annotations

from typing import Callable, Generic, Sequence, TypeVar, overload

__all__ = ["querymixin", "recursemixin"]


T = TypeVar("T")


def matcher(expr: str) -> Callable[[T], bool]:
    """Returns True if the expression returns True. The context for the
    expression is the element.

    Given a class:

    >>> class A:
    ...     def __init__(self, name):
    ...         self.name = name

    We can create a path for each object:

    >>> a = A("root")
    >>> a.a = A("level1")
    >>> a.b = A("b")
    >>> a.a.text = "help"

    If we want to match, ``it`` is used to refer to the subjected object:

    >>> matcher('it.name=="root"')(a)
    True
    >>> matcher('it.b.name=="b"')(a)
    True
    >>> matcher('it.name=="blah"')(a)
    False
    >>> matcher('it.nonexistent=="root"')(a)
    False

    NOTE: the object ``it`` was introduced since properties (descriptors) can
    not be executed from within a dictionary context.
    """

    compiled = compile(expr, "<matcher>", "eval")

    def real_matcher(element: T) -> bool:
        try:
            return bool(eval(compiled, {}, {"it": element}))
        except (AttributeError, NameError):
            # attribute does not (yet) exist
            return False

    return real_matcher


class querymixin:
    """Implementation of the matcher as a mixin for lists.

    Given a class:

    >>> class A:
    ...     def __init__(self, name):
    ...         self.name = name

    We can do nice things with this list:

    >>> class MList(querymixin, list):
    ...     pass
    >>> m = MList()
    >>> m.append(A("one"))
    >>> m.append(A("two"))
    >>> m.append(A("three"))
    >>> m[1].name
    'two'
    >>> m['it.name=="one"']  # doctest: +ELLIPSIS
    [<gaphor.core.modeling.listmixins.A object at 0x...>]
    >>> m['it.name=="two"', 0].name
    'two'
    """

    def __getitem__(self, key):
        try:
            # See if the list can deal with it (don't change default behaviour)
            return super().__getitem__(key)  # type: ignore[misc] # noqa: F821
        except TypeError:
            # Nope, try our matcher trick
            if isinstance(key, tuple):
                key, remainder = key[0], key[1:]
            else:
                remainder = None

            matched = list(filter(matcher(key), self))  # type: ignore[call-overload] # noqa: F821
            new_list = type(self)(matched)  # type: ignore[call-arg] # noqa: F821
            return new_list.__getitem__(*remainder) if remainder else new_list


def issafeiterable(obj):
    """Checks if the object is iterable, but not a string.

    >>> issafeiterable([])
    True
    >>> issafeiterable(set())
    True
    >>> issafeiterable({})
    True
    >>> issafeiterable(1)
    False
    >>> issafeiterable("text")
    False
    """
    try:
        return iter(obj) and not isinstance(obj, str)
    except TypeError:
        pass
    return False


class recurseproxy(Generic[T]):
    """Proxy object (helper) for the recusemixin.

    The proxy has limited capabilities compared to a real list (or set):
    it can be iterated and a getitem can be performed. On the other
    side, the type of the original sequence is maintained, so getitem
    operations act as if they're executed on the original list.
    """

    def __init__(self, sequence: Sequence[T]):
        self.__sequence = sequence

    def __getitem__(self, key: int | slice) -> T:
        return self.__sequence.__getitem__(key)  # type: ignore[return-value]

    def __iter__(self):
        """Iterate over the items.

        If there is some level of nesting, the parent items are iterated
        as well.
        """
        return iter(self.__sequence)

    def __getattr__(self, key: str) -> recurseproxy[T]:
        """Create a new proxy for the attribute."""

        def mygetattr():
            sentinel = object()
            for e in self.__sequence:
                obj = getattr(e, key, sentinel)
                if obj is sentinel:
                    pass
                elif issafeiterable(obj):
                    yield from obj  # type: ignore[misc]
                else:
                    yield obj

        # Create a copy of the proxy type, including a copy of the sequence type
        return type(self)(type(self.__sequence)(mygetattr()))  # type: ignore[call-arg]


class recursemixin(Generic[T]):
    """Mixin class for lists, sets, etc. If data is requested using ``[:]``, a
    ``recurseproxy`` instance is created.

    The basic idea is to have a class that can contain children:

    >>> class A:
    ...     def __init__(self, name, *children):
    ...         self.name = name
    ...         self.children = list(children)
    ...
    ...     def dump(self, level=0):
    ...         print(" " * level, self.name)
    ...         for c in self.children:
    ...             c.dump(level + 1)

    Now if we make a (complex) structure out of it:

    >>> a = A("root", A("a", A("b"), A("c"), A("d")), A("e", A("one"), A("two")))
    >>> a.dump()  # doctest: +ELLIPSIS
     root
      a
       b
       c
       d
      e
       one
       two
    >>> a.children[1].name
    'e'

    Given ``a``, I want to iterate all grand-children (b, c, d, one, two) and
    the structure I want to do that with is:

      ``a.children[:].children``

    In order to do this we have to use a special list class, so we can handle
    our specific case. ``__getslice__`` should be overridden, so we can make it
    behave like a normal python object (legacy, yes...).

    >>> class rlist(recursemixin, list):
    ...     pass
    >>> class A:
    ...     def __init__(self, name, *children):
    ...         self.name = name
    ...         self.children = rlist(children)
    ...
    ...     def dump(self, level=0):
    ...         print(" " * level, self.name)
    ...         for c in self.children:
    ...             c.dump(level + 1)

    >>> a = A("root", A("a", A("b"), A("c"), A("d")), A("e", A("one"), A("two")))
    >>> a.children[1].name
    'e'

    Invoking ``a.children[:]`` should now return a recurseproxy object:

    >>> a.children[:]  # doctest: +ELLIPSIS
    <gaphor.core.modeling.listmixins.recurseproxy object at 0x...>
    >>> list(a.children[:].name)  # doctest: +ELLIPSIS
    ['a', 'e']

    Now calling a child on the list will return a list of all children:

    >>> a.children[:].children  # doctest: +ELLIPSIS
    <gaphor.core.modeling.listmixins.recurseproxy object at 0x...>
    >>> list(a.children[:].children)  # doctest: +ELLIPSIS
    [<gaphor.core.modeling.listmixins.A object at 0x...>, <gaphor.core.modeling.listmixins.A object at 0x...>, <gaphor.core.modeling.listmixins.A object at 0x...>, <gaphor.core.modeling.listmixins.A object at 0x...>, <gaphor.core.modeling.listmixins.A object at 0x...>]

    And of course we're interested in the names:

    >>> a.children[:].children.name  # doctest: +ELLIPSIS
    <gaphor.core.modeling.listmixins.recurseproxy object at 0x...>
    >>> list(a.children[:].children.name)
    ['b', 'c', 'd', 'one', 'two']
    """

    _recursemixin_trigger = slice(None, None, None)

    def proxy_class(self):
        return recurseproxy

    @overload
    def __getitem__(self, key: int) -> T:
        ...

    @overload
    def __getitem__(self, key: slice) -> recurseproxy[T]:
        ...

    def __getitem__(self, key):
        if key == self._recursemixin_trigger:
            return self.proxy_class()(self)
        else:
            return super().__getitem__(key)  # type: ignore[misc] # noqa: F821
