# -* encoding: uft-8 *-

from requests import Response

from ..static.defines import NOT_FOUND
from ..static.errors import EntryCreatedError, OperationCompletionError, ResponseError


class RPMessage(object):
    __slots__ = ["message", "error_code"]

    def __init__(self, data):
        assert isinstance(data, dict)

        self.message = data.get("message", NOT_FOUND)
        self.error_code = data.get("error_code", NOT_FOUND)

    def __str__(self):
        if self.error_code is NOT_FOUND:
            return self.message
        return "{error_code}: {message}".format(error_code=self.error_code, message=self.message)

    @property
    def is_empty(self):
        return self.message is NOT_FOUND


class RPResponse(object):
    __slots__ = ["_data"]

    def __init__(self, data):
        # type: (Response) -> None
        self._data = self._to_json(data)  # type: dict

    @staticmethod
    def _get_json(data):
        # type: (Response) -> dict
        if not data.text:
            return {}

        try:
            return data.json()
        except ValueError as error:
            raise ResponseError("Invalid response: {}: {}".format(error, data.text))

    @property
    def json(self):
        return self._data

    @property
    def is_success(self):
        return True

    @property
    def id(self):
        return self.json.get("id", NOT_FOUND)

    @property
    def message(self):
        return self.json.get("msg", NOT_FOUND)

    @property
    def messages(self):
        return tuple(self.iter_messages())

    def iter_messages(self):
        data = self.json.get("responses", [self.json])

        for chunk in data:
            message = RPMessage(chunk)
            if not message.is_empty:
                yield message

    # ---- OLD ---

    def _get_id(self, response):
        try:
            return self._get_data(response)["id"]
        except KeyError:
            raise EntryCreatedError(
                "No 'id' in response: {0}".format(response.text))

    def _get_msg(self, response):
        try:
            return self._get_data(response)["msg"]
        except KeyError:
            raise OperationCompletionError(
                "No 'msg' in response: {0}".format(response.text))

    def _get_data(self, response):
        data = self._to_json(response)
        error_messages = self._get_messages(data)
        error_count = len(error_messages)

        if error_count == 1:
            raise ResponseError(error_messages[0])
        elif error_count > 1:
            raise ResponseError(
                "\n  - ".join(["Multiple errors:"] + error_messages))
        elif not response.ok:
            response.raise_for_status()
        elif not data:
            raise ResponseError("Empty response")
        else:
            return data

    def _to_json(self, response):
        try:
            if response.text:
                return response.json()
            else:
                return {}
        except ValueError as value_error:
            raise ResponseError(
                "Invalid response: {0}: {1}".format(value_error, response.text))

    def _get_messages(self, data):
        error_messages = []
        for ret in data.get("responses", [data]):
            if "message" in ret:
                if "error_code" in ret:
                    error_messages.append(
                        "{0}: {1}".format(ret["error_code"], ret["message"]))
                else:
                    error_messages.append(ret["message"])

        return error_messages
