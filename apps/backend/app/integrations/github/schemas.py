from pydantic import BaseModel


class GitHubWebhookEvent(BaseModel):
    action: str | None = None
    repository: dict | None = None
    sender: dict | None = None
