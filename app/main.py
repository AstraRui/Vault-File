import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.v1.routes import router as secrets_router
from app.core.config import get_settings
from app.core.crypto import get_crypto_service
from app.core.exceptions import AppError, PayloadTooLargeError
from app.core.logging import setup_logging
from app.repositories.secret_repository import get_secret_repository
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

TAGS_METADATA = [
    {
        "name": "secrets",
        "description": "Создание и одноразовое чтение зашифрованных секретов (текст и файлы).",
    },
    {
        "name": "health",
        "description": "Проверка работоспособности сервиса и доступности Redis.",
    },
]

APP_DESCRIPTION = """
Микросервис одноразовых зашифрованных ссылок (аналог Mozilla Send).

Текст и файлы шифруются на бэкенде одним и тем же ключом (Fernet) и хранятся
в Redis. Чтение — атомарная операция **GETDEL**: ссылка физически не может
быть открыта дважды. Дополнительно запись уничтожается по истечении TTL.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(get_settings())
    logger.info("File Vault запускается")
    get_crypto_service()  # валидируем ENCRYPTION_KEY на старте, а не на первом запросе
    await get_secret_repository().ping()  # проверяем, что Redis реально доступен
    yield
    await get_secret_repository().close()
    logger.info("File Vault остановлен")


app = FastAPI(
    title="File Vault",
    description=APP_DESCRIPTION,
    version="0.1.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)


@app.middleware("http")
async def limit_request_size(request: Request, call_next: Callable[[Request], Awaitable]):
    """Ранний отказ по заявленному Content-Length — не допускает чтение тела запроса,
    превышающего лимит, в память (до вызова обработчика и парсинга JSON/формы).
    Клиент, лгущий о Content-Length (например, chunked-encoding), этой проверкой не
    ловится — для файлов отдельная потоковая проверка есть в самом загрузочном роуте.
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        settings = get_settings()
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        if int(content_length) > max_bytes:
            exc = PayloadTooLargeError(settings.max_file_size_mb)
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Awaitable]):
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        # С двумя наложенными @app.middleware("http") Starlette иногда не даёт
        # этому call_next вернуть уже обработанный exception_handler'ом ответ —
        # исключение всплывает и сюда. Фиксируем сам факт сбоя и даём ему пройти
        # дальше: унести его в тишину — значит потерять запись о сбойном запросе.
        duration_ms = (time.monotonic() - start) * 1000
        logger.error(
            "%s %s -> исключение после %.1f ms", request.method, request.url.path, duration_ms
        )
        raise

    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Последний рубеж: любое необработанное исключение (обрыв Redis, баг и т.п.)
    логируется с полным traceback и не просачивается клиенту как есть.
    """
    logger.critical(
        "Необработанное исключение на %s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


app.include_router(secrets_router, prefix="/api/v1")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    responses={503: {"description": "Redis недоступен"}},
)
async def health_check() -> HealthResponse:
    try:
        await get_secret_repository().ping()
    except Exception as exc:
        logger.error("Health check failed: Redis unreachable (%s)", exc)
        raise HTTPException(status_code=503, detail="Redis недоступен") from exc

    return HealthResponse(status="ok", redis="ok")


# Монтируется последним: API-роуты выше по приоритету, всё остальное отдаёт статику фронтенда
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
