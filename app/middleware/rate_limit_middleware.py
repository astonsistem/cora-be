from fastapi import Request

from app.core.config.config import settings
from app.core.security.rate_limiter import RateLimiter


class RateLimitGuard:
    def __init__(self, scope: str, limit_per_minute: int, trust_proxy: bool | None = None):
        self.scope = scope
        self.limiter = RateLimiter(limit_per_minute, 60)
        self.trust_proxy = settings.trust_proxy_headers if trust_proxy is None else trust_proxy

    def client_ip(self, request: Request) -> str:
        if self.trust_proxy:
            forwarded = request.headers.get("x-forwarded-for", "")
            first = forwarded.split(",")[0].strip()
            if first:
                return first
        return request.client.host if request.client else "unknown"

    def __call__(self, request: Request) -> None:
        self.limiter.hit(f"{self.scope}:{self.client_ip(request)}")


public_guard = RateLimitGuard("public", settings.public_rate_limit_per_minute)
submit_guard = RateLimitGuard("submit", settings.public_submit_rate_limit_per_minute)
code_guard = RateLimitGuard("code", settings.public_code_rate_limit_per_minute)
