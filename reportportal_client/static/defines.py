# -* encoding: uft-8 *-


class PresenceSentinel(object):
    def __nonzero__(self):
        return False

    __bool__ = __nonzero__  # Python3 support


NOT_FOUND = NOT_SET = PresenceSentinel()
NoneType = type(None)
