from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from core.config import get_settings
from core.database import dispose_engine
from core.exceptions import AppError
from core.logging import logger
from core.redis import close_redis
from middleware.logging import RequestLoggingMiddleware
from routes.auth import router as auth_router
from routes.clients import router as clients_router
from routes.health import router as health_router
from routes.users import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting SNS Hub backend")
    yield
    logger.info("Shutting down SNS Hub backend")
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="AimTop SNS Hub",
        version="0.1.0",
        lifespan=lifespan,
    )

    _add_cors(application, settings.CORS_ORIGINS)
    _add_exception_handlers(application)
    _add_middleware(application)
    _register_routers(application)

    return application


def _add_cors(application: FastAPI, origins: list[str]) -> None:
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _add_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(AppError)
    async def app_error_handler(
        _request: Request,
        exc: AppError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.message},
        )

    @application.exception_handler(ValidationError)
    async def validation_error_handler(
        _request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"success": False, "message": str(exc)},
        )

    @application.exception_handler(Exception)
    async def generic_error_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.error("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error"},
        )


def _add_middleware(application: FastAPI) -> None:
    application.add_middleware(RequestLoggingMiddleware)


def _register_routers(application: FastAPI) -> None:
    application.include_router(health_router)
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(users_router, prefix="/api/v1")
    application.include_router(clients_router, prefix="/api/v1")


app = create_app()
