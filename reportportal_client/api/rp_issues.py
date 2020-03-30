

class Issue:

    def __init__(self,
                 issue_type,
                 comment=None,
                 auto_analyzed=False,
                 ignore_analyzer=False):
        self._external_issues = []
        self.auto_analyzed = auto_analyzed
        self.comment = comment
        self.ignore_analyzer = ignore_analyzer
        self.issue_type = issue_type

    def external_issue_add(self, issue):
        self._external_issues.append(issue.payload)

    @property
    def payload(self):
        return {
            'autoAnalyzed': self.auto_analyzed,
            'comment': self.comment,
            'externalSystemIssues': self._external_issues,
            'ignoreAnalyzer': self.ignore_analyzer,
            'issueType': self.issue_type
        }


class ExternalIssue(object):
    def __init__(self,
                 bts_url=None,
                 bts_project=None,
                 submit_date=None,
                 ticket_id=None,
                 url=None):
        self.bts_url = bts_url
        self.bts_project = bts_project
        self.submit_date = submit_date
        self.ticket_id = ticket_id
        self.url = url

    @property
    def payload(self):
        return {
            'brsUrl': self.bts_url,
            'btsProject': self.bts_project,
            'submitDate': self.submit_date,
            'ticketId': self.ticket_id,
            'url': self.url
        }