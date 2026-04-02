from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from core.config import settings
from core.database import init_db
from routes import auth, users, clients, health, onboarding
from routes import contents, channels, dashboard, media
from routes import oauth, publish, ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("서버 시작 중...")
    try:
        await init_db()
        logger.info("DB 초기화 완료")
    except Exception as e:
        logger.warning(f"DB 초기화 실패 (DB 미연결): {e}")
    yield
    logger.info("서버 종료")


app = FastAPI(
    title="AimTop SNS Hub API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    logger.info(f"{request.method} {request.url.path} {response.status_code} {duration}ms")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 오류가 발생했습니다"}
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(clients.router)
app.include_router(onboarding.router)
app.include_router(contents.router)
app.include_router(channels.router)
app.include_router(dashboard.router)
app.include_router(media.router)
app.include_router(oauth.router)
app.include_router(publish.router)
app.include_router(ai.router)
