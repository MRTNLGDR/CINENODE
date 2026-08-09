from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import ipaddress

from .config import Settings


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        public = path in {"/", "/health", "/api/health", "/favicon.svg"} or path.startswith("/web/")
        client = request.client.host if request.client else ""
        if self.settings.mode == "local":
            try:
                local = ipaddress.ip_address(client).is_loopback
            except ValueError:
                local = client in {"localhost", "testclient"}
            if not local and not self.settings.test_mode:
                return JSONResponse({"detail": "CineNode local mode accepts loopback clients only"}, 403)
        if not public and self.settings.mode == "server":
            supplied = request.headers.get("x-cinenode-token")
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                supplied = auth[7:]
            if supplied != self.settings.auth_token:
                return JSONResponse({"detail": "authentication required"}, 401)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'",
        )
        return response
