from app.services.github_service import GitHubService


class GitHubClient:
    def __init__(self) -> None:
        self.service = GitHubService()

    def create_pull_request(self, title: str, body: str) -> dict[str, str | None]:
        return self.service.open_real_pr(title=title, body=body)
