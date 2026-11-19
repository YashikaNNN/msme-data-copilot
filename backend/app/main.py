import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.database import init_db
from app.errors import AppError

logger = logging.getLogger("msme")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    init_db()
    logger.info("MSME Data Copilot API ready")
    yield


app = FastAPI(title="MSME Data Copilot API", version="1.0.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list or ["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RateLimitMiddleware:
    def __init__(self, app, limit: int = 240, window: int = 60) -> None:
        self.app = app
        self.limit = limit
        self.window = window
        self.hits: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path.startswith("/api/") and not path.endswith("/health"):
            client = scope.get("client")
            ip = client[0] if client else "local"
            now = time.time()
            recent = [stamp for stamp in self.hits[ip] if now - stamp < self.window]
            if len(recent) >= self.limit:
                response = JSONResponse(
                    {"detail": "Too many requests. Wait a moment and try again."},
                    status_code=429,
                )
                await response(scope, receive, send)
                return
            recent.append(now)
            self.hits[ip] = recent[-self.limit :]
        await self.app(scope, receive, send)


app.add_middleware(RateLimitMiddleware)


@app.exception_handler(AppError)
async def app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": exc.message})


@app.get("/")
def root() -> dict:
    return {"name": "MSME Data Copilot", "docs": "/docs", "health": "/api/v1/health"}


app.include_router(router)
