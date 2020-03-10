#  Copyright (c) 2018 http://reportportal.io
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import collections
import json
import logging
import uuid

from api.dispatcher import APIDispatcher

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ReportPortalService(object):
    """
    Service class with report portal event callbacks.
    """
    DEFAULT_API_BASE = "api/v1"

    def __init__(self, endpoint, project, token, api_base=DEFAULT_API_BASE,
                 investigate_skipped=True, verify_ssl=True, retries=None):
        """
        Init the service class.

        :param endpoint: endpoint of the report portal service
        :param project: project name to use for launch names
        :param token: authorization token
        :param api_base: an API version, defaults to latest stable path slice
        :param investigate_skipped: an option not to mark skipped tests 'To Investigate' on the server side
        :param verify_ssl: option to not verify ssl certificates
        :param retries: number of retries for HTTP(S) adapters
        """

        self._api = APIDispatcher(endpoint=endpoint, project=project, token=token, api_base=api_base,
                                  verify_ssl=verify_ssl, retries=retries)
        self.investigate_skipped = investigate_skipped
        self.launch_id = None

    def terminate(self):
        """
        Intentionally empty method, nothing to do on terminate
        """

    def start_launch(self, name, start_time=None, description=None, tags=None, mode=None):
        return self._api.start_launch(name=name, start_time=start_time)

    def _finalize_launch(self, end_time, action, status):
        data = {
            "end_time": end_time,
            "status": status
        }
        url = uri_join(self.base_url, "launch", self.launch_id, action)
        r = self.session.put(url=url, json=data, verify=self.verify_ssl)
        self.stack.pop()
        logger.debug("%s_launch - Stack: %s", action, self.stack)
        return _get_msg(r)

    def finish_launch(self, end_time, status=None):
        return self._finalize_launch(end_time=end_time, action="finish",
                                     status=status)

    def stop_launch(self, end_time, status=None):
        return self._finalize_launch(end_time=end_time, action="stop",
                                     status=status)

    def start_test_item(self, name, start_time, item_type, description=None,
                        tags=None, parameters=None):
        """
        item_type can be (SUITE, STORY, TEST, SCENARIO, STEP, BEFORE_CLASS,
        BEFORE_GROUPS, BEFORE_METHOD, BEFORE_SUITE, BEFORE_TEST, AFTER_CLASS,
        AFTER_GROUPS, AFTER_METHOD, AFTER_SUITE, AFTER_TEST)

        parameters should be a dictionary with the following format:
            {
                "<key1>": "<value1>",
                "<key2>": "<value2>",
                ...
            }
        """
        if parameters is not None:
            parameters = [{"key": key, "value": str(value)}
                          for key, value in parameters.items()]

        data = {
            "name": name,
            "description": description,
            "tags": tags,
            "start_time": start_time,
            "launch_id": self.launch_id,
            "type": item_type,
            "parameters": parameters,
        }
        parent_item_id = self.stack[-1]
        if parent_item_id is not None:
            url = uri_join(self.base_url, "item", parent_item_id)
        else:
            url = uri_join(self.base_url, "item")
        r = self.session.post(url=url, json=data, verify=self.verify_ssl)

        item_id = _get_id(r)
        self.stack.append(item_id)
        logger.debug("start_test_item - Stack: %s", self.stack)
        return item_id

    def finish_test_item(self, end_time, status, issue=None):
        # check if skipped test should not be marked as "TO INVESTIGATE"
        if issue is None and status == "SKIPPED" and not self.investigate_skipped:
            issue = {"issue_type": "NOT_ISSUE"}

        data = {
            "end_time": end_time,
            "status": status,
            "issue": issue,
        }
        item_id = self.stack.pop()
        url = uri_join(self.base_url, "item", item_id)
        r = self.session.put(url=url, json=data, verify=self.verify_ssl)
        logger.debug("finish_test_item - Stack: %s", self.stack)
        return _get_msg(r)

    def log(self, time, message, level=None, attachment=None):
        data = {
            "item_id": self.stack[-1] or self.launch_id,
            "time": time,
            "message": message,
            "level": level,
        }
        if attachment:
            data["attachment"] = attachment
            return self.log_batch([data])
        else:
            url = uri_join(self.base_url, "log")
            r = self.session.post(url=url, json=data, verify=self.verify_ssl)
            logger.debug("log - Stack: %s", self.stack)
            return _get_id(r)

    def log_batch(self, log_data):
        """Logs batch of messages with attachment.

        Args:
            log_data: list of log records.
            log record is a dict of;
                time, message, level, attachment
                attachment is a dict of:
                    name: name of attachment
                    data: fileobj or content
                    mime: content type for attachment

        """

        url = uri_join(self.base_url, "log")

        attachments = []
        for log_item in log_data:
            log_item["item_id"] = self.stack[-1]
            attachment = log_item.get("attachment", None)

            if "attachment" in log_item:
                del log_item["attachment"]

            if attachment:
                if not isinstance(attachment, collections.Mapping):
                    attachment = {"data": attachment}

                name = attachment.get("name", str(uuid.uuid4()))
                log_item["file"] = {"name": name}
                attachments.append(("file", (
                    name,
                    attachment["data"],
                    attachment.get("mime", "application/octet-stream")
                )))

        files = [(
            "json_request_part", (
                None,
                json.dumps(log_data),
                "application/json"
            )
        )]
        files.extend(attachments)
        from reportportal_client import POST_LOGBATCH_RETRY_COUNT
        for i in range(POST_LOGBATCH_RETRY_COUNT):
            try:
                r = self.session.post(
                    url=url,
                    files=files,
                    verify=self.verify_ssl
                )
            except KeyError:
                if i < POST_LOGBATCH_RETRY_COUNT - 1:
                    continue
                else:
                    raise
            break

        logger.debug("log_batch - Stack: %s", self.stack)
        logger.debug("log_batch response: %s", r.text)

        return _get_data(r)
