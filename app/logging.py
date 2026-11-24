"""Structured Logging and Request Context."""
import logging
import sys
import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configure root logger
logging_level = logging.INFO
logging.basicConfig(
    level=logging_level,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("hotel_pms")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for injecting Request-ID and logging structured request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start_time = time.perf_counter()

        logger.info(
            f"req_start id={request_id} method={request.method} path={request.url.path} "
            f"client={request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration_ms}ms"

            logger.info(
                f"req_done id={request_id} method={request.method} path={request.url.path} "
                f"status={response.status_code} duration={duration_ms}ms"
            )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"req_fail id={request_id} method={request.method} path={request.url.path} "
                f"error={str(exc)} duration={duration_ms}ms",
                exc_info=True,
            )
            raise
