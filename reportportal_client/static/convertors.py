
import six


def _convert_string(value):
    """Support and convert strings in py2 and py3.
    :param value: input string
    :return value: convert string
    """
    if isinstance(value, six.text_type):
        # Don't try to encode 'unicode' in Python 2.
        return value
    return str(value)


def _dict_to_payload(dictionary):
    """Convert dict to list of dicts.
    :param dictionary: initial dict
    :return list: list of dicts
    """
    system = dictionary.pop('system', None)
    payload = [
        {'key': key, 'value': _convert_string(value)}
        for key, value in sorted(dictionary.items()) if value
    ]
    if system is not None:
        for dc in payload:
            dc['system'] = system
    return payload