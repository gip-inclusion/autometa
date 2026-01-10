"""HTML page routes."""

import re

from flask import Blueprint, render_template, request

from ..storage import store
from ..helpers import validate_knowledge_path, list_knowledge_files, list_staged_files
from .conversations import get_agent_instance

bp = Blueprint("html", __name__)


def humanize_title(title: str) -> str:
    """Clean up a title: strip date prefix, ISO timestamps, separators; capitalize."""
    if not title:
        return title
    title = re.sub(r"^\d{4}-\d{2}(-\d{2})?[-_]?", "", title)
    title = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?", "", title)
    title = re.sub(r"[-_]+", " ", title)
    if title:
        title = title[0].upper() + title[1:]
    return title.strip()


def get_sidebar_data():
    """Get data for sidebar (conversations only, reports are now in DB)."""
    conversations = store.list_conversations(limit=10)
    agent = get_agent_instance()

    running_ids = []
    for conv in conversations:
        if conv.title:
            conv.title = humanize_title(conv.title)
        conv.is_running = agent.is_running(conv.id)
        if conv.is_running:
            running_ids.append(conv.id)

    return {"conversations": conversations, "running_ids": running_ids}


@bp.route("/")
def index():
    """Redirect to explorations."""
    data = get_sidebar_data()
    return render_template("explorations.html", section="explorations", **data)


@bp.route("/explorations")
def explorations():
    """Explorations section - chat interface."""
    data = get_sidebar_data()
    current_conv_id = request.args.get("conv")
    current_conv = None
    if current_conv_id:
        current_conv = store.get_conversation(current_conv_id, include_messages=False)
        if current_conv and current_conv.title:
            current_conv.title = humanize_title(current_conv.title)
    return render_template("explorations.html", section="explorations", current_conv=current_conv, **data)


@bp.route("/connaissances")
def connaissances():
    """Connaissances section - knowledge file browser."""
    data = get_sidebar_data()
    file_param = request.args.get("file")
    conv_id = request.args.get("conv")

    current_file = None
    file_content = None
    current_conv = None
    staged_files = []

    if file_param:
        validated_path = validate_knowledge_path(file_param)
        if validated_path:
            current_file = file_param
            file_content = validated_path.read_text()

            if conv_id:
                current_conv = store.get_conversation(conv_id, include_messages=False)
            else:
                current_conv = store.get_active_knowledge_conversation(file_param)

            if current_conv:
                staged_files = list_staged_files(current_conv.id)
        else:
            return render_template(
                "connaissances.html",
                section="connaissances",
                error="Fichier non trouve",
                categories=list_knowledge_files(),
                active_conversations=store.list_active_knowledge_conversations(),
                **data
            )

    categories = list_knowledge_files()
    active_conversations = store.list_active_knowledge_conversations()
    active_files = {c.file_path: c for c in active_conversations if c.file_path}

    return render_template(
        "connaissances.html",
        section="connaissances",
        categories=categories,
        current_file=current_file,
        file_content=file_content,
        current_conv=current_conv,
        staged_files=staged_files,
        active_files=active_files,
        active_conversations=active_conversations,
        **data
    )
