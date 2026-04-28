import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.v1.profiles import router as profile_router
from app.api.v1.auth import router as auth_router
from app.db.session import engine, Base
from app.middleware.versioning import api_version_middleware
from app.middleware.logging import logging_middleware
from app.middleware.rate_limits import rate_limit_middleware
from seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed()
    yield


app = FastAPI(lifespan=lifespan)

app.middleware("http")(logging_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(api_version_middleware)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    for error in exc.errors():
        if "name" in error.get("loc", []):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Missing or empty name"},
            )
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Invalid type"},
    )


@app.exception_handler(404)
async def not_found_exception_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"status": "error", "message": "Profile not found"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["*"],
)

app.include_router(profile_router, prefix="/api", tags=["Profiles"])
app.include_router(auth_router)


@app.get("/")
def root():
    return {"message": "Welcome to the HNG Stage Three  API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

