import time
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.config import settings
from app.core.database import db_manager

async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Simple Redis-based Rate Limiting Middleware.
    Bypasses rate limiting for IP addresses in RATE_LIMIT_WHITELIST.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Bypass whitelist
    whitelist = [ip.strip() for ip in settings.RATE_LIMIT_WHITELIST.split(",") if ip.strip()]
    if client_ip in whitelist or client_ip == "unknown":
        return await call_next(request)

    # Determine rate limit based on path
    is_auth_route = request.url.path.startswith("/api/auth")
    limit = settings.RATE_LIMIT_AUTH_PER_MINUTE if is_auth_route else settings.RATE_LIMIT_PER_MINUTE

    # Use Redis to track requests
    try:
        redis = db_manager.redis
        current_minute = int(time.time() // 60)
        redis_key = f"rate_limit:{client_ip}:{current_minute}"

        # Increment request count
        request_count = await redis.incr(redis_key)
        
        # Set expiry for 2 minutes to clean up
        if request_count == 1:
            await redis.expire(redis_key, 120)

        if request_count > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )
    except Exception:
        # If Redis fails, degrade gracefully (allow request)
        pass

    return await call_next(request)
