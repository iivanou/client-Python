import inspect
import types

from .rp_response import RPResponse


class CommunicationSpecBase(object):
    def __init__(self, path, method, response_type=None):
        # type: (str, types.FunctionType, RPResponse) -> None
        assert isinstance(path, str)
        assert inspect.isroutine(method)

        self.path = path
        self.method = method

    def __call__(self, api_dispatcher):
        # type: (APIDispatcher) -> RPResponse
        result = self.method()
        return RPResponse(result)


class LogItemSpec(CommunicationSpecBase):
    def __init__(self, path, method):
        super().__init__(path, method)
