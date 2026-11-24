import sys
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

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
    from the '__p' query parameter injected by vercel.json rewrites, or
    from Vercel headers.
    """
    def __init__(self, inner_app):
        self.inner_app = inner_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            query_bytes = scope.get("query_string", b"")
            query_str = query_bytes.decode("latin-1") if query_bytes else ""

            target_path = None
            if "__p=" in query_str:
                params = parse_qsl(query_str, keep_blank_values=True)
                filtered_params = []
                for k, v in params:
                    if k == "__p":
                        target_path = v
                    else:
                        filtered_params.append((k, v))
                # Update query_string without __p
                clean_query = urlencode(filtered_params)
                scope["query_string"] = clean_query.encode("latin-1")

            # Fallback to headers if not in query param
            if not target_path:
                headers = dict(scope.get("headers", []))
                for header_key in (b"x-matched-path", b"x-forwarded-uri", b"x-vercel-sc-path", b"x-invoke-path"):
                    val = headers.get(header_key, b"").decode("latin-1")
                    if val and val.split("?")[0] not in ("/api/index.py", "/api/index", "/api"):
                        target_path = val.split("?")[0]
                        break

            if target_path:
                clean_path = target_path.split("?")[0]
                if not clean_path.startswith("/"):
                    clean_path = "/" + clean_path
                while clean_path.startswith("//"):
                    clean_path = clean_path[1:]
                if clean_path in ("/api/index.py", "/api/index", "/api"):
                    clean_path = "/"
                scope["path"] = clean_path
                scope["raw_path"] = clean_path.encode("latin-1")
            elif scope.get("path") in ("/api/index.py", "/api/index", "/api"):
                scope["path"] = "/"
                scope["raw_path"] = b"/"

        await self.inner_app(scope, receive, send)


app = VercelPathFixMiddleware(fastapi_app)
