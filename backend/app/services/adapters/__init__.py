from app.services.adapters.asana import AsanaAdapter
from app.services.adapters.base import NormalizedTicket, TicketAdapter
from app.services.adapters.github import GitHubIssueAdapter
from app.services.adapters.jira import JiraAdapter
from app.services.adapters.linear import LinearAdapter

ADAPTERS: dict[str, TicketAdapter] = {
    "jira": JiraAdapter(),
    "linear": LinearAdapter(),
    "github": GitHubIssueAdapter(),
    "asana": AsanaAdapter(),
}

__all__ = ["ADAPTERS", "NormalizedTicket", "TicketAdapter"]
