import time
from collections import defaultdict, deque
from fastapi import Request
from fastapi.responses import JSONResponse

# storing request per IP
request_logs = defaultdict(deque)

AUTH_LIMT = 10
GENERAL_LIMIT = 60

WINDOW_SECONDs = 60


async def rate_limit_middleware(request: Request, call_next):
    now = time.time()
    
    #identifying the client
    client_ip = request.client.host
    
    path = request.url.path
    
    if path.startswith("/auth"):
        limit = AUTH_LIMT
        key = f"auth:{client_ip}"
    else:
        limit = GENERAL_LIMIT
        key = f"general:{client_ip}"
    
    #get request history
    timestamps = request_logs[key]
    print(timestamps)
    
    while timestamps and timestamps[0] <= now - WINDOW_SECONDs:
        timestamps.popleft()
    
    if len(timestamps) > limit:
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "message": "Too many requests"
            }
        )
    
    timestamps.append(now)
    
    response = await call_next(request)
    return response