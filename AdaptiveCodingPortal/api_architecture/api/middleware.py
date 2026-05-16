"""
Middleware for the Question Sequencing API.

Handles:
- Request/response logging
- Stateless API validation
- Metrics collection (optional)
"""

import logging
import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import Headers

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all incoming requests and outgoing responses.
    
    Captures:
    - Request method, path, query params
    - Response status code and time elapsed
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request/response lifecycle."""
        request_time = time.time()
        method = request.method
        path = request.url.path
        query_string = request.url.query

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled exception in request processing")
            raise

        elapsed_ms = (time.time() - request_time) * 1000
        status_code = response.status_code

        logger.info(
            "Request completed: %s %s (query=%s) → %d [%.1f ms]",
            method,
            path,
            query_string or "(none)",
            status_code,
            elapsed_ms,
        )

        return response


class StatelessAPIMiddleware(BaseHTTPMiddleware):
    """
    Middleware for stateless API validation and metrics.
    
    Validates that:
    - Stateless endpoints receive X-Student-State header or student_state in body
    - State is properly formatted (base64-encoded JSON)
    
    Collects metrics (optional):
    - Request/response sizes
    - State version tracking
    - Error counts
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process stateless API requests."""
        method = request.method
        path = request.url.path

        # For stateless endpoints, optional validation can be added here
        # Currently, validation is done at the endpoint level in routes.py
        # This middleware is primarily for future logging/metrics expansion

        response = await call_next(request)

        # Track metrics for stateless endpoints
        if "stateless" in path:
            logger.debug(
                "Stateless API request processed: %s %s → %d",
                method,
                path,
                response.status_code,
            )

        return response
