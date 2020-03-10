# -* encoding: uft-8 *-


class _PresenceSentinel(object):
    def __nonzero__(self):
        """
        Added to handle a conditional situation on attributes that are this __class__ objects:
        >>> if not response.error:
        where response.error can be NOT_FOUND or NOT_SET
        :return: bool
        """
        return False

    __bool__ = __nonzero__  # Python3 support


NOT_FOUND = NOT_SET = _PresenceSentinel()
NoneType = type(None)
