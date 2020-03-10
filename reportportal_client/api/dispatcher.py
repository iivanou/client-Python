# -* encoding: uft-8 *-
import logging
import typing

import requests
from requests.adapters import HTTPAdapter

from .items import RPItem
from .rp_response import RPResponse
from ..static.defines import NOT_SET

__all__ = ["APIDispatcher"]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

RP_LOG_LEVELS = {
    60000: "UNKNOWN",
    50000: "FATAL",
    40000: "ERROR",
    30000: "WARN",
    20000: "INFO",
    10000: "DEBUG",
    5000: "TRACE"
}


class APIDispatcher(object):
    """
    Middleware for interfacing API to the user methods and DTOs.
    A middleman between an RP service and requests library

    The API description: https://github.com/reportportal/documentation/blob/master/src/md/src/DevGuides/reporting.md
    Endpoints list: https://github.com/reportportal/documentation/blob/master/src/md/src/DevGuides/api-differences.md
    """

    DEFAULT_ADAPTER_RETRIES = 0
    PROTOCOLS = ["http://", "https://"]

    def __init__(self, endpoint, api_base, project, token, verify_ssl=True, retries=DEFAULT_ADAPTER_RETRIES):
        self._api_endpoint = endpoint  # type: str
        self._api_base = api_base  # type: str
        self._project = project  # type: str

        self._token = token  # type: str
        self._session = requests.Session()  # type : requests.Session
        self._launch = None  # type: typing.Optional[RPItem]

        # A function that generates timestamp for each start and stop call
        self._time_producer = None

        self.base_url = URIUtils.uri_join(endpoint, api_base, project)  # type: str
        self.verify_ssl = verify_ssl  # type: bool

        self._setup_session(retries=retries)

    def _setup_session(self, retries=DEFAULT_ADAPTER_RETRIES, headers=None):
        # type: (int,  typing.Optional[dict]) -> APIDispatcher
        assert isinstance(retries, int)
        if retries:
            for protocol in self.PROTOCOLS:
                self._session.mount(protocol, HTTPAdapter(max_retries=retries))

        session_headers = self._get_authorization_header_spec()
        if headers is not None:
            session_headers.update(headers)

        self._session.headers.update(session_headers)
        return self

    def _get_authorization_header_spec(self):
        # type: () -> typing.Dict[str, str]
        assert self._token is not None
        return {"Authorization": "bearer {}".format(self._token)}

    def _build_path(self, *items):
        return URIUtils.uri_join(self.base_url, *items)

    def _get(self, url):
        # type: (str) -> RPResponse
        response_data = self._session.get(url=url, verify=self.verify_ssl)
        return RPResponse(response_data)

    def _post(self, url, data):
        # type: (str, typing.Optional[typing.Union[list, dict]]) -> RPResponse
        response_data = self._session.post(url=url, json=data, verify=self.verify_ssl)
        return RPResponse(response_data)

    def _put(self, url, data):
        # type: (str, typing.Optional[typing.Union[list, dict]]) -> RPResponse
        response_data = self._session.put(url=url, json=data, verify=self.verify_ssl)
        return RPResponse(response_data)

    def logger_add_handler(self, handler):
        # type: (logging.Handler) -> bool
        """
        Add a handler to the logger handlers list, if the handler is not yet in there.

        :param handler: a logger handler to add
        :return: True if the handler was added, otherwise False because it is already there
        """
        if handler in logger.handlers:
            return False

        logger.addHandler(handler)
        return True

    def set_time_producer(self, producer):
        """
        Allows setting a callable to automatically get a time string in a predefined format.
        For instance:
        >>> set_time_producer(lambda: time.strftime("%a, %d %b %Y %H:%M:%S +0000"))

        :param producer: a callable that constructs current time in string format
        :return: nothing
        """
        assert callable(producer) or producer is None
        self._time_producer = producer

    def _update_data(self, data, name, value):
        # type: (dict, str, typing.Any) -> None
        if value is NOT_SET:
            return
        data[name] = value

    # === Public methods to interact with the RP service
    @property
    def launch_id(self):
        return self._launch.uuid

    def _prepare_start_launch(self, name, start_time, description, uuid, attributes, mode, rerun, rerun_of):
        data = {}
        self._update_data(data, "name", name)
        self._update_data(data, "startTime", start_time or self._time_producer())

        self._update_data(data, "description", description)
        self._update_data(data, "uuid", uuid)
        self._update_data(data, "attributes", attributes)
        self._update_data(data, "tags", attributes)
        self._update_data(data, "mode", mode)
        self._update_data(data, "rerun", rerun)
        self._update_data(data, "rerunOf", rerun_of)
        return data

    def _prepare_start_item(self, name, start_time, item_type, launch_uuid, description, attributes, uuid,
                            code_ref, parameters, unique_id, retry, has_stats):
        if parameters is not NOT_SET:
            parameters = [{"key": key, "value": str(value)} for key, value in parameters.items()]

        data = {}
        self._update_data(data, "name", name)
        self._update_data(data, "startTime", start_time or self._time_producer())
        self._update_data(data, "type", item_type)
        self._update_data(data, "launchUuid", launch_uuid)
        self._update_data(data, "description", description)
        self._update_data(data, "attributes", attributes)
        self._update_data(data, "tags", attributes)
        self._update_data(data, "uuid", uuid)
        self._update_data(data, "codeRef", code_ref)
        self._update_data(data, "parameters", parameters)
        self._update_data(data, "uniqueId", unique_id)
        self._update_data(data, "retry", retry)
        self._update_data(data, "hasStats", has_stats)
        return data

    def _prepare_finish_item(self, end_time, launch_uuid, status, description, attributes, retry, issue):
        data = {}
        self._update_data(data, "endTime", end_time or self._time_producer())
        self._update_data(data, "launchUuid", launch_uuid)
        self._update_data(data, "status", status)
        self._update_data(data, "description", description)
        self._update_data(data, "attributes", attributes)
        self._update_data(data, "tags", attributes)
        self._update_data(data, "retry", retry)
        self._update_data(data, "issue", issue)
        return data

    def start_launch(self, name, start_time=None,
                     # Optional arguments
                     description=NOT_SET, uuid=NOT_SET, attributes=NOT_SET, mode=NOT_SET,
                     rerun=NOT_SET, rerun_of=NOT_SET):
        """
        To start launch you should send request to the following endpoint: POST /api/{version}/{projectName}/launch

        :param name:        Name of launch
        :param start_time:  Launch start time. Ex.
                            2019-11-22T11:47:01+00:00 (ISO 8601);
                            Fri, 22 Nov 2019 11:47:01 +0000 (RFC 822, 1036, 1123, 2822);
                            2019-11-22T11:47:01+00:00 (RFC 3339);
                            1574423221000 (Unix Timestamp)
        :param description: Description of launch
        :param uuid:        Launch uuid (string identifier)
        :param attributes:  Launch attributes(tags). Pairs of key and value
        :param mode:        Launch mode. Allowable values 'default' or 'debug'
        :param rerun:       Rerun mode. Allowable values 'true' of 'false'
        :param rerun_of:    Rerun mode. Specifies launch to be re-ran. Uses with 'rerun' attribute.
        :return:
        """
        assert start_time or self._time_producer

        data = self._prepare_start_launch(name, start_time, description, uuid, attributes, mode, rerun, rerun_of)
        return self._post(url=self._build_path("launch"), data=data).id

    def start_item(self, name, start_time=NOT_SET,
                   # Optional arguments
                   item_type=NOT_SET, launch_uuid=NOT_SET, description=NOT_SET, attributes=NOT_SET, uuid=NOT_SET,
                   code_ref=NOT_SET, parameters=NOT_SET, unique_id=NOT_SET, retry=NOT_SET, has_stats=NOT_SET):
        """
        To start root item you should send request to the following endpoint: POST /api/{version}/{projectName}/item

        :param name:        Name of test item
        :param start_time:  Test item start time
        :param item_type:   Type of test item. Allowable values: "suite", "story", "test", "scenario", "step",
                            "before_class", "before_groups", "before_method", "before_suite", "before_test",
                            "after_class", "after_groups", "after_method", "after_suite", "after_test"
        :param launch_uuid: Parent launch UUID
        :param description: Test item description
        :param attributes:  Test item attributes(tags). Pairs of key and value. Ex. most failed, os:android
        :param uuid:        Test item UUID. Auto generated.
        :param code_ref:    Physical location of test item. Ex. com.rpproject.tests.LoggingTests
        :param parameters:  Set of parameters (for parametrized tests)
        :param unique_id:   Auto generated.
        :param retry:       Used to report retry of test. Allowable values: 'true' or 'false'
        :param has_stats:   ?
        :return:
        """
        assert start_time or self._time_producer

        data = self._prepare_start_item(name, start_time, item_type, launch_uuid, description, attributes, uuid,
                                        code_ref, parameters, unique_id, retry, has_stats)
        return self._post(url=self._build_path("item"), data=data).id

    def start_child_item(self, parent_uuid, name, start_time=NOT_SET,
                         # Optional arguments
                         item_type=NOT_SET, launch_uuid=NOT_SET, description=NOT_SET, attributes=NOT_SET, uuid=NOT_SET,
                         code_ref=NOT_SET, parameters=NOT_SET, unique_id=NOT_SET, retry=NOT_SET, has_stats=NOT_SET):
        """
        To start child item we need know launch UUID and parent test item UUID.
        We should call the following endpoint: POST /api/{version}/{projectName}/item/{parentItemUuid}
        :return:
        """
        data = self._prepare_start_item(name, start_time, item_type, launch_uuid, description, attributes, uuid,
                                        code_ref, parameters, unique_id, retry, has_stats)
        return self._post(url=self._build_path("item", parent_uuid), data=data).id

    def finish_item(self, item_uuid, launch_uuid, end_time=None,
                    # Optional arguments
                    status=NOT_SET, description=NOT_SET, attributes=NOT_SET, retry=NOT_SET, issue=NOT_SET,
                    need_investigate_skipped=True):
        """
        To finish the test item we should send the following request: PUT /api/{version}/{projectName}/item/{itemUuid}
        If item finished successfully in the response will be message with item uuid.

        :param item_uuid:   Item UUID to finish
        :param end_time:    Test item end time. Ex.
                            2019-11-22T11:47:01+00:00 (ISO 8601);
                            Fri, 22 Nov 2019 11:47:01 +0000 (RFC 822, 1036, 1123, 2822);
                            2019-11-22T11:47:01+00:00 (RFC 3339);
                            1574423221000 (Unix Timestamp)
        :param launch_uuid: Parent launch UUID
        :param status:      Test item status.
                            Allowable values: "passed", "failed", "stopped", "skipped", "interrupted", "cancelled".
        :param description: Test item description. Overrides description from start request.
        :param attributes:  Test item attributes(tags). Pairs of key and value. Overrides attributes on start
        :param retry:       Used to report retry of test. Allowable values: 'true' or 'false'
        :param issue:       Issue of current test item. Custom structure.
        :param need_investigate_skipped:
        :return:
        """
        # check if skipped test should not be marked as "TO INVESTIGATE"
        if issue is None and status.lower() == "skipped" and not need_investigate_skipped:
            issue = {"issue_type": "NOT_ISSUE"}

        data = self._prepare_finish_item(end_time, launch_uuid, status, description, attributes, retry, issue)
        return self._put(url=self._build_path("item", item_uuid), data=data).message

    def _prepare_save_log(self, launch_uuid, time, item_uuid, message, level, file_data):
        data = {}
        self._update_data(data, "launchUuid", launch_uuid)
        self._update_data(data, "time", time or self._time_producer())
        self._update_data(data, "itemUuid", item_uuid)
        self._update_data(data, "message", message)
        self._update_data(data, "level", level)
        self._update_data(data, "file", file_data)
        return data

    def save_log(self, project_name, launch_uuid, time,
                 # Optional arguments
                 item_uuid=NOT_SET, message=NOT_SET, level=NOT_SET, attachments=NOT_SET):
        """
        We can save logs for test items. It is not necessary to save log when test item already finished.
        We can create log for test item with in_progress status.
        Common endpoint: POST /api/{version}/{projectName}/log

        :param project_name:Project name
        :param launch_uuid: Launch UUID
        :param time:        Log time
        :param item_uuid:   Test item UUID
        :param message:     Log message
        :param level:       Log level.  Allowable values: error(40000), warn(30000), info(20000),
                            debug(10000), trace(5000), fatal(50000), unknown(60000)
        :param attachments: a dict of:
                    name: name of attachment
                    data: file object or content
                    mime: content type for attachment
        :return:
        """
        data = self._prepare_save_log(launch_uuid, time, item_uuid, message, level, file_data=NOT_SET)
        return self._post(URIUtils.uri_join(project_name, "log"), data=data).message

    def save_log_batch(self):
        pass

    def update_test_item(self, item_uuid, description=None, tags=None):
        """
        Update test item.
        :param item_uuid:
        :param description: test item description
        :param tags: test item tags
        """
        data = {
            "description": description,
            "tags": tags,
        }

        return self._put(URIUtils.uri_join(self.base_url, "item", item_uuid, "update"), data=data).message

    def get_project_settings(self):
        return self._get(URIUtils.uri_join(self.base_url, "settings")).json


class URIUtils(object):
    @staticmethod
    def uri_join(*uri_parts):
        # type: (typing.Tuple[str]) -> str
        """
        Join the uri parts.
        Avoid usage of urlparse.urljoin and os.path.join as it does not clearly join parts.

        :param uri_parts: tuple of values for join, can contain back and forward
                            slashes (will be stripped up).
        :return: An URI string
        """
        return "/".join(str(s).strip("/").strip("\\") for s in uri_parts)
