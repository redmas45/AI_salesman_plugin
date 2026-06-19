"""FastAPI middleware: request tracing, security headers, and rate limiting."""

from collections import defaultdict, deque
from collections.abc import Callable
import logging
import threading
import time
import uuid

from fastapi import Request, Response
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_SECONDS = 60
RATE_LIMIT_RULES: tuple[tuple[str, int, int], ...] = (
    ("/v1/admin", 120, DEFAULT_WINDOW_SECONDS),
    ("/v1/client-panel/login", 10, DEFAULT_WINDOW_SECONDS),
    ("/v1/catalog/crawler/run", 5, DEFAULT_WINDOW_SECONDS),
    ("/v1/shop", 60, DEFAULT_WINDOW_SECONDS),
    ("/v1/client-log", 120, DEFAULT_WINDOW_SECONDS),
)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and log timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.perf_counter()

        logger.info(
            "REQ  | id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )

        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        logger.info(
            "RESP | id=%s status=%d time=%.0fms",
            request_id,
            response.status_code,
            elapsed_ms,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach conservative browser security headers to HTTP responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        path = request.url.path

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        if path == "/crm" or path.startswith("/crm/"):
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: http: https:; "
                "connect-src 'self'; "
                "font-src 'self' data:; "
                "object-src 'none'; "
                "base-uri 'none'; "
                "frame-ancestors 'none'",
            )
        elif path.startswith("/v1/admin"):
            response.headers.setdefault("Cache-Control", "no-store")

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Small in-process rate limiter for sensitive and expensive routes."""

    def __init__(self, app, rules: tuple[tuple[str, int, int], ...] = RATE_LIMIT_RULES):
        super().__init__(app)
        self.rules = rules
        self.hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rule = self._matching_rule(request.url.path)
        if rule:
            prefix, limit, window_seconds = rule
            retry_after = self._register_hit(
                key=(self._client_ip(request), prefix),
                limit=limit,
                window_seconds=window_seconds,
            )
            if retry_after > 0:
                return JSONResponse(
                    {"detail": "Too many requests. Try again shortly."},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)

    def _matching_rule(self, path: str) -> tuple[str, int, int] | None:
        for prefix, limit, window_seconds in self.rules:
            if path.startswith(prefix):
                return prefix, limit, window_seconds
        return None

    def _register_hit(self, *, key: tuple[str, str], limit: int, window_seconds: int) -> int:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self.lock:
            bucket = self.hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return max(1, int(window_seconds - (now - bucket[0])))
            bucket.append(now)
        return 0

    def _client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()[:80]
        return (request.client.host if request.client else "unknown")[:80]
