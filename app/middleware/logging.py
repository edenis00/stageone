import time
import logging
from fastapi import Request
from starlette.responses import Response


logger = logging.getLogger("insighta_logger")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)


async def logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    process_time = time.perf_counter() - start_time
    
    # Change your logger call to look like this:
    logger.info(
        "%s %s | Status: %s | Response time: %ss", 
        request.method, 
        request.url.path, 
        response.status_code, 
        process_time
    )
    
    return response