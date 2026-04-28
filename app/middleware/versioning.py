from fastapi import Request, status
from fastapi.responses import JSONResponse


async def api_version_middleware(request: Request, call_next):
    if request.url.path.startswith("/api"):
        version = request.headers.get("X-API-Version")
        
        if not version:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "API version header required"
                }
            )
        
        if version != "1":
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Invalid API version",
                },
            )
        
    response = await call_next(request)
    return response 