"""Event Manager."""

from collections import deque

from generic.event import Event, Handler
from generic.event import Manager as _Manager

from gaphor.abc import Service


def event_handler(*event_types):
    """Mark a function/method as an event handler for a particular type of
    event."""

    def wrapper(func):
        func.__event_types__ = event_types
        return func

    return wrapper


class EventManager(Service):
    """The Event Manager."""

    def __init__(self) -> None:
        self._events = _Manager()
        self._queue: deque[Event] = deque()
        self._handling = False

    def shutdown(self) -> None:
        pass

    def subscribe(self, handler: Handler) -> None:
        """Register a handler.

        Handlers are triggered (executed) when specific events are
        emitted through the handle() method.
        """
        event_types = getattr(handler, "__event_types__", None)
        if not event_types:
            raise Exception(f"No event types provided for function {handler}")

        for et in event_types:
            self._events.subscribe(handler, et)

    def unsubscribe(self, handler: Handler) -> None:
        """Unregister a previously registered handler."""
        event_types = getattr(handler, "__event_types__", None)
        if not event_types:
            raise Exception(f"No event types provided for function {handler}")

        for et in event_types:
            self._events.unsubscribe(handler, et)

    def handle(self, *events: Event) -> None:
        """Send event notifications to registered handlers."""
        queue = self._queue
        queue.extendleft(events)

        if not self._handling:
            self._handling = True
            try:
                while queue:
                    self._events.handle(queue.pop())
            finally:
                self._handling = False
