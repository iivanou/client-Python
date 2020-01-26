# -* encoding: uft-8 *-
from abc import ABC, abstractmethod


class RPRequestBase(ABC):
    @abstractmethod
    def to_json(self):
        pass


class LaunchStartRequest(RPRequestBase):
    def __init__(self, name, start_time,
                 description=None, uuid=None, attributes=None, mode=None, rerun=None, rerun_of=None):
        self.name = name
        self.start_time = start_time
        self.description = description
        self.uuid = uuid
        self.attributes = attributes
        self.mode = mode
        self.rerun = rerun
        self.rerun_of = rerun_of

    def prepare(self):
        return


class ItemStartRequest(RPRequestBase):
    def __init__(self, name, start_time, type_, launch_uuid,
                 description, attributes, uuid, code_ref, parameters, unique_id, retry, has_stats):
        self.name = name
        self.start_time = start_time
        self.type_ = type_
        self.launch_uuid = launch_uuid
        self.description = description
        self.attributes = attributes
        self.uuid = uuid
        self.code_ref = code_ref
        self.parameters = parameters
        self.unique_id = unique_id
        self.retry = retry
        self.has_stats = has_stats


class ItemFinishRequest(RPRequestBase):
    def __init__(self, end_time, launch_uuid, status, description, attributes, retry, issue):
        self.end_time = end_time
        self.launch_uuid = launch_uuid
        self.status = status
        self.description = description
        self.attributes = attributes
        self.retry = retry
        self.issue = issue  # type: IssueType


class SaveLog(RPRequestBase):
    def __init__(self, launch_uuid, time, item_uuid, message, level):
        self.launch_uuid = launch_uuid
        self.time = time
        self.item_uuid = item_uuid
        self.message = message
        self.level = level


class SaveLogBatch(RPRequestBase):
    def __init__(self, name, content, content_type):
        self.name = name
        self.content = content
        self.content_type = content_type


class SaveLaunchLog(SaveLog):
    """
    It is possible to report log attached to launch.
    To do that use the same log endpoint, but in body do not send itemUuid
    """


# ==
class IssueType(object):
    def __init__(self, issue_type, comment, auto_analyzed, ignore_analyzer, external_system_issues):
        """

        :param issue_type:  Issue type locator.
                            Allowable values: "pb***", "ab***", "si***", "ti***", "nd001". Where *** is locator id.
        :param comment:     Issue comment. Ex. "Framework issue. Script outdated"
        :param auto_analyzed:   Is issue was submitted by auto analyzer
        :param ignore_analyzer: Is issue should be ignored during auto analysis
        :param external_system_issues:  Set of external system issues.
        """
        self.issue_type = issue_type
        self.comment = comment
        self.auto_analyzed = auto_analyzed
        self.ignore_analyzer = ignore_analyzer
        self.external_system_issues = external_system_issues
