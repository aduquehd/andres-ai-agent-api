from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter

from config import settings
from modules.admin.routers import router as admin_router
from modules.chats.routers import router as chats_router
from modules.utils.redis import init_redis
from modules.utils.sentry import init_sentry


# Initialize Sentry before creating the FastAPI app
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = await init_redis()
    await FastAPILimiter.init(redis_client)
    yield
    await FastAPILimiter.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "X-Browser-Id", "Content-Type"],
)

app.include_router(chats_router, prefix="/api/chats")
app.include_router(admin_router)

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_fastapi(app)
logfire.instrument_asyncpg()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
