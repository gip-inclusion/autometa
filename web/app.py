"""Autometa web application - FastAPI server with SSE streaming."""

import asyncio
import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import PurePosixPath

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import config, sync_to_s3
from . import s3 as s3_module
from .interactive_apps import scan_interactive_apps
from .log import setup_logging
from .redis_conn import close_redis
from .runner import runner
from .sentry import init_sentry, set_user_context
from .warmup import run as warmup

# FIXME(vperron): have a logging level config ?
setup_logging(level=logging.DEBUG if config.DEBUG else logging.INFO)
# Silence noisy third-party loggers (boto generates ~30 debug lines per S3 request)
# FIXME(vperron): There were other noisy ones.
for _logger_name in ("botocore", "boto3", "urllib3", "s3transfer", "httpcore", "watchfiles"):
    logging.getLogger(_logger_name).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# FIXME(vperron): In main() maybe ?
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown tasks."""
    # Warmup (cache rebuild) runs in background — app serves requests immediately
    warmup_task = asyncio.create_task(asyncio.to_thread(warmup))
    sync_to_s3.start_sync_watcher()

    await asyncio.to_thread(scan_interactive_apps)
    await runner.startup()

    yield

    warmup_task.cancel()
    await runner.shutdown()
    await close_redis()


# Create FastAPI app
app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def sentry_user_middleware(request: Request, call_next):
    """Attach the authenticated user to every Sentry event/transaction."""
    email = request.headers.get("X-Forwarded-Email") or config.DEFAULT_USER
    set_user_context(email)
    return await call_next(request)


app.mount("/static", StaticFiles(directory="web/static"), name="static")

if config.COMMON_DIR.exists():
    app.mount("/common", StaticFiles(directory=str(config.COMMON_DIR)), name="common")


_STATIC_ASSET_EXTS = frozenset({
    ".css",
    ".js",
    ".mjs",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".map",
})


@app.get("/interactive/{filename:path}")
@app.get("/interactive/")
def serve_interactive(request: Request, filename: str = ""):
    if filename.endswith(".py"):
        raise HTTPException(status_code=404)

    if not filename or filename.endswith("/"):
        filename = filename + "index.html"

    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=404)

    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"
    cache_control = "no-cache" if mime_type == "text/html" else "public, max-age=3600"

    suffix = PurePosixPath(filename).suffix.lower()
    if suffix in _STATIC_ASSET_EXTS and s3_module.interactive.exists(filename):
        url = s3_module.interactive.get_url(filename, expires_in=300)
        if url is not None:
            return RedirectResponse(
                url,
                status_code=307,
                headers={"Cache-Control": "private, max-age=300", "Referrer-Policy": "no-referrer"},
            )

    stream = s3_module.interactive.stream(filename)
    if stream is not None:
        return StreamingResponse(stream, media_type=mime_type, headers={"Cache-Control": cache_control})

    raise HTTPException(status_code=404)


from .benchmark import router as benchmark_router  # noqa: E402
from .routes import auth, conversations, cron, html, knowledge, query, reports  # noqa: E402
from .selftest import router as selftest_router  # noqa: E402

app.include_router(selftest_router)
app.include_router(benchmark_router)
app.include_router(query.router)
app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(reports.api_router)
app.include_router(conversations.router)
# Template-serving routers last (they have catch-all-ish paths)
app.include_router(reports.html_router)
app.include_router(cron.router)
app.include_router(html.router)


def main():
    """Run the development server."""
    print(f"Starting Autometa web server at http://{config.HOST}:{config.PORT}")
    print(f"Agent backend: {config.AGENT_BACKEND}")
    print(f"Working directory: {config.BASE_DIR}")

    uvicorn.run(
        "web.app:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        workers=config.WEB_WORKERS,
    )


if __name__ == "__main__":
    main()
