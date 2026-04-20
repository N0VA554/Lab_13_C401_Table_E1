from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clear contextvars to avoid leakage between requests
        clear_contextvars()

        # Extract x-request-id from headers or generate a new one
        # Format: req-<8-char-hex>
        header_id = request.headers.get("x-request-id")
        correlation_id = header_id if header_id else f"req-{uuid.uuid4().hex[:8]}"
        
        # Bind the correlation_id to structlog contextvars
        bind_contextvars(correlation_id=correlation_id)
        
        request.state.correlation_id = correlation_id
        
        start = time.perf_counter()
        response = await call_next(request)
        
        # Add the correlation_id and processing time to response headers
        process_time_ms = int((time.perf_counter() - start) * 1000)
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(process_time_ms)
        
        return response
