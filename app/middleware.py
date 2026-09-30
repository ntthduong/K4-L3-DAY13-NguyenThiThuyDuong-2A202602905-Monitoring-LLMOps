from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        clear_contextvars()

        # Only accept IDs in our documented format; don't propagate arbitrary
        # client input into logs or traces.
        supplied_id = request.headers.get("x-request-id", "")
        if len(supplied_id) == 12 and supplied_id.startswith("req-"):
            suffix = supplied_id[4:]
            if all(char in "0123456789abcdefABCDEF" for char in suffix):
                correlation_id = supplied_id
            else:
                correlation_id = f"req-{uuid.uuid4().hex[:8]}"
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"
        
        bind_contextvars(correlation_id=correlation_id)
        
        request.state.correlation_id = correlation_id
        
        start = time.perf_counter()
        response = await call_next(request)
        
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{(time.perf_counter() - start) * 1000:.2f}"
        
        return response
