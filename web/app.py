"""Autometa web application - FastAPI server with SSE streaming."""

import asyncio
import logging
import mimetypes
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles

from . import config, sync_to_s3
from . import s3 as s3_module
from .interactive_apps import scan_interactive_apps
from .logging_utils import setup_logging
from .redis_conn import close_redis
from .runner import runner

setup_logging(level=logging.DEBUG if config.DEBUG else logging.INFO)
# Silence noisy third-party loggers (boto generates ~30 debug lines per S3 request)
for _logger_name in ("botocore", "boto3", "urllib3", "s3transfer"):
    logging.getLogger(_logger_name).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown tasks."""
    sync_to_s3.start_sync_watcher()

    await asyncio.to_thread(scan_interactive_apps)
    await runner.startup()

    yield

    await runner.shutdown()
    await close_redis()


# Create FastAPI app
app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="web/static"), name="static")

if config.COMMON_DIR.exists():
    app.mount("/common", StaticFiles(directory=str(config.COMMON_DIR)), name="common")


@app.get("/interactive/{filename:path}")
@app.get("/interactive/")
def serve_interactive(request: Request, filename: str = ""):
    """Serve static files from S3, proxied to avoid exposing internal endpoints."""
    if filename.endswith(".py"):
        raise HTTPException(status_code=404)

    if not filename or filename.endswith("/"):
        filename = filename + "index.html"

    # Path traversal protection
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=404)

    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"
    cache_control = "no-cache" if mime_type == "text/html" else "public, max-age=3600"

    content = s3_module.download_file(filename)
    if content is not None:
        return Response(
            content=content,
            media_type=mime_type,
            headers={"Cache-Control": cache_control},
        )

    raise HTTPException(status_code=404)


from .benchmark import router as benchmark_router  # noqa: E402
from .routes import auth, conversations, cron, html, knowledge, query, rapports, reports  # noqa: E402
from .selftest import router as selftest_router  # noqa: E402

app.include_router(selftest_router)
app.include_router(benchmark_router)
app.include_router(query.router)
app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(reports.router)
app.include_router(conversations.router)
# Template-serving routers last (they have catch-all-ish paths)
app.include_router(rapports.router)
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
