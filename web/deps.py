"""Shared FastAPI dependencies and template helpers."""

import os
import re

import markdown as md_lib
import nh3
from fastapi import Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from . import config
from .helpers import format_relative_date


def get_current_user(request: Request) -> str:
    return request.headers.get("X-Forwarded-Email") or config.DEFAULT_USER


def get_current_user_name(request: Request) -> str | None:
    return request.headers.get("X-Forwarded-User")


templates = Jinja2Templates(directory="web/templates")

# Custom filters


def regex_replace_filter(value, pattern, replacement=""):
    return re.sub(pattern, replacement, str(value))


templates.env.filters["regex_replace"] = regex_replace_filter


def markdown_filter(text: str | None) -> Markup:
    """Render agent-authored markdown to HTML, sanitized — the source text is not trusted."""
    html = md_lib.markdown(text or "", extensions=["fenced_code", "tables", "sane_lists"])
    return Markup(nh3.clean(html))


templates.env.filters["markdown"] = markdown_filter


def static_url(path: str) -> str:
    try:
        mtime = int(os.path.getmtime(f"web/static/{path}"))
    except OSError:
        mtime = 0
    return f"/static/{path}?v={mtime}"


templates.env.globals["static_url"] = static_url

templates.env.globals["format_relative_date"] = format_relative_date

templates.env.globals["matomo_tracking_url"] = config.MATOMO_TRACKING_URL
templates.env.globals["matomo_tag_manager_container_id"] = config.MATOMO_TAG_MANAGER_CONTAINER_ID
