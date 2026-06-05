from app.services.adapters.base import NormalizedTicket, TicketAdapter
from app.services.adapters.github import GitHubIssueAdapter
from app.services.adapters.jira import JiraAdapter
from app.services.adapters.linear import LinearAdapter

ADAPTERS: dict[str, TicketAdapter] = {
    "jira": JiraAdapter(),
    "linear": LinearAdapter(),
    "github": GitHubIssueAdapter(),
}

__all__ = ["ADAPTERS", "NormalizedTicket", "TicketAdapter"]
