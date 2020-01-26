# -* encoding: uft-8 *-
import typing


class RPItem(object):
    __slots__ = ["uuid", "parent", "_child_items", "_is_active"]

    def __init__(self, uuid, parent=None):
        # type: (typing.Optional[RPItem], typing.Optional[RPItem]) -> None
        self.uuid = uuid
        self.parent = parent

        self._child_items = set()  # type: typing.Set[RPItem]
        self._is_active = True

    def __iter__(self):
        return iter(self._child_items)

    @property
    def is_active(self):
        return self._is_active

    def set_parent(self, parent_item):
        # type: (RPItem, RPItem) -> None
        if self.parent is not None:
            return
        self.parent = parent_item

    def add_child(self, child):
        # type: (RPItem) -> None
        child.set_parent(self)
        self._child_items.add(child)

    def complete(self, nested=False):
        if self.is_active:
            self._is_active = False

        if not nested:
            return

        for child in self._child_items:
            child.complete(nested=nested)


class RPItemManager(object):
    def __init__(self):
        self._launch = None

    def start_launch(self):
        pass

    def stop_launch(self):
        pass
