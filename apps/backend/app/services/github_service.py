from app.core.config import settings


class GitHubService:
    def validate_config(self) -> tuple[bool, str]:
        if not settings.ALLOW_REAL_GITHUB_PR:
            return False, "Real GitHub PR creation is disabled by ALLOW_REAL_GITHUB_PR=false."
        if not settings.GITHUB_TOKEN:
            return False, "GITHUB_TOKEN is required to create a real PR."
        if not settings.GITHUB_TARGET_OWNER or not settings.GITHUB_TARGET_REPO:
            return False, "GITHUB_TARGET_OWNER and GITHUB_TARGET_REPO are required."
        if not settings.ALLOW_EXTERNAL_WRITE_ACTIONS:
            return False, "External write actions are disabled by ALLOW_EXTERNAL_WRITE_ACTIONS=false."
        return True, "GitHub configuration is valid."

    def create_draft_pr(self, title: str, body: str) -> dict[str, str | None]:
        return {"status": "planned", "title": title, "body": body, "url": None}

    def open_real_pr(self, title: str, body: str) -> dict[str, str | None]:
        valid, message = self.validate_config()
        if not valid:
            raise ValueError(message)
        return {"status": "skipped", "title": title, "body": body, "url": None}
