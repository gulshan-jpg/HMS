import sys
import os
from pathlib import Path

# Add project root and /var/task to sys.path
root_dir = Path(__file__).resolve().parent.parent
for p in [str(root_dir), "/var/task", os.getcwd()]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app as fastapi_app


class VercelPathFixMiddleware:
    """
    Vercel internal rewrites rewrite the incoming URL to /api/index.py.
    This ASGI middleware intercepts the request and restores scope['path']
    from the original URL passed in 'x-matched-path' or 'x-forwarded-uri'.
    """
    def __init__(self, inner_app):
        self.inner_app = inner_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            headers = dict(scope.get("headers", []))

            # Check headers injected by Vercel containing original client URL
            raw_matched = headers.get(b"x-matched-path", b"")
            if not raw_matched:
                raw_matched = headers.get(b"x-forwarded-uri", b"")
            if not raw_matched:
                raw_matched = headers.get(b"x-invoke-path", b"")

            matched_path = raw_matched.decode("latin-1") if raw_matched else ""
            current_path = scope.get("path", "")

            if matched_path:
                clean_path = matched_path.split("?")[0]
                if clean_path and clean_path not in ("/api/index.py", "/api/index", "/api"):
                    scope["path"] = clean_path
            elif current_path in ("/api/index.py", "/api/index", "/api"):
                # Direct invocation fallback to root landing page
                scope["path"] = "/"

        await self.inner_app(scope, receive, send)


app = VercelPathFixMiddleware(fastapi_app)
