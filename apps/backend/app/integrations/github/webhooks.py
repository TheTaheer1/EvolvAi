from app.core.security import verify_github_signature


def verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    return verify_github_signature(secret, body, signature)
