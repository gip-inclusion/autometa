"""Agents screen: each agent, its runs and deliveries, and the review queue approved from the session."""

import logging
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from lib import agent_config, agent_delivery
from web import config
from web.config import ADMIN_USERS
from web.db import get_db
from web.deps import get_current_user, templates
from web.models import Agent, AgentDelivery, AgentRun

from .html import get_sidebar_data

logger = logging.getLogger(__name__)

router = APIRouter()

# Why: a status reached once someone has decided; any other means the delivery never awaited review.
DECIDED = ("pending_send", "sending", "sent", "failed", "refused", "rejected")

Slug = Annotated[str, PathParam(pattern=r"^[a-z][a-z0-9-]{2,40}$")]


def same_origin(request: Request) -> None:
    """Why: the session is oauth2-proxy's cookie, which a form posted from another site would carry too."""
    site = request.headers.get("sec-fetch-site")
    origin = urlparse(request.headers.get("origin") or "").netloc
    if site == "same-origin" or (site is None and origin and origin == request.headers.get("host")):
        return
    raise HTTPException(status_code=403, detail="requête venue d'une autre origine")


def may_review(user_email: str, owner_email: str) -> bool:
    return user_email == owner_email or user_email in ADMIN_USERS


def modes(agent: Agent) -> list[str]:
    return sorted({c["mode"] for c in agent.config["destinations"]})


def review_queue(user_email: str) -> list[dict]:
    with get_db() as session:
        rows = session.execute(
            select(AgentDelivery, Agent)
            .join(AgentRun, AgentRun.id == AgentDelivery.run_id)
            .join(Agent, Agent.id == AgentRun.agent_id)
            .where(AgentDelivery.status == "pending_review", Agent.status == "active")
            .order_by(AgentDelivery.id)
        ).all()
        return [
            {**agent_delivery.as_dict(d), "agent": a.slug, "may_review": may_review(user_email, a.owner_email)}
            for d, a in rows
        ]


def agent_rows() -> list[dict]:
    with get_db() as session:
        agents = session.scalars(select(Agent).order_by(Agent.status, Agent.slug)).all()
        last_runs = {
            r.agent_id: {"status": r.status, "launched_at": r.launched_at}
            for r in session.scalars(
                select(AgentRun).distinct(AgentRun.agent_id).order_by(AgentRun.agent_id, AgentRun.launched_at.desc())
            )
        }
        waiting = dict(
            session.execute(
                select(AgentRun.agent_id, func.count(AgentDelivery.id))
                .join(AgentDelivery, AgentDelivery.run_id == AgentRun.id)
                .where(AgentDelivery.status == "pending_review")
                .group_by(AgentRun.agent_id)
            ).all()
        )
        return [
            {
                "slug": a.slug,
                "title": a.config["title"],
                "owner": a.owner_email,
                "status": a.status,
                "modes": modes(a),
                "cadence": agent_config.cadence(a.config.get("schedule")),
                "last_run": last_runs.get(a.id),
                "waiting": waiting.get(a.id, 0),
            }
            for a in agents
        ]


@router.get("/agents")
def agents_page(request: Request, user_email: str = Depends(get_current_user)):
    return templates.TemplateResponse(
        request,
        "agents.html",
        {
            "section": "agents",
            "agents": agent_rows(),
            "queue": review_queue(user_email),
            **get_sidebar_data(user_email, request),
        },
    )


@router.get("/agents/{slug}")
def agent_page(slug: Slug, request: Request, user_email: str = Depends(get_current_user)):
    with get_db() as session:
        agent = session.scalar(select(Agent).where(Agent.slug == slug))
        if agent is None:
            raise HTTPException(status_code=404)
        runs = session.scalars(
            select(AgentRun).where(AgentRun.agent_id == agent.id).order_by(AgentRun.launched_at.desc()).limit(20)
        ).all()
        deliveries = session.scalars(
            select(AgentDelivery)
            .join(AgentRun, AgentRun.id == AgentDelivery.run_id)
            .where(AgentRun.agent_id == agent.id)
            .order_by(AgentDelivery.id.desc())
            .limit(50)
        ).all()
        return templates.TemplateResponse(
            request,
            "agent_detail.html",
            {
                "section": "agents",
                "agent": agent,
                "lines": agent_config.describe(agent.config),
                "targets": set(config.AGENT_DESTINATION_TARGETS),
                "runs": runs,
                "deliveries": [
                    {**agent_delivery.as_dict(d), "may_review": may_review(user_email, agent.owner_email)}
                    for d in deliveries
                ],
                **get_sidebar_data(user_email, request),
            },
        )


def reviewed(delivery_id: int, user_email: str) -> JSONResponse | None:
    """The answer refusing this reviewer, or None when they may decide on the delivery."""
    with get_db() as session:
        owner = session.scalar(
            select(Agent.owner_email)
            .join(AgentRun, AgentRun.agent_id == Agent.id)
            .join(AgentDelivery, AgentDelivery.run_id == AgentRun.id)
            .where(AgentDelivery.id == delivery_id)
        )
    if owner is None:
        return JSONResponse({"error": "envoi introuvable"}, status_code=404)
    if not may_review(user_email, owner):
        return JSONResponse({"error": "seul le propriétaire de l'agent ou un administrateur décide"}, status_code=403)
    return None


def not_pending(exc: agent_delivery.DeliveryNotPending) -> JSONResponse:
    """A fixed answer for each refusal; the exception's text stays on the server."""
    logger.info("agent envoi : décision refusée, statut %s", exc.status)
    if exc.status is None:
        return JSONResponse({"error": "envoi introuvable"}, status_code=404)
    if exc.status in DECIDED:
        return JSONResponse({"error": "envoi déjà décidé"}, status_code=409)
    return JSONResponse({"error": "cet envoi n'attend pas de relecture"}, status_code=409)


@router.post("/api/agents/deliveries/{delivery_id}/approve", dependencies=[Depends(same_origin)])
def approve_delivery(delivery_id: int, user_email: str = Depends(get_current_user)):
    if refused := reviewed(delivery_id, user_email):
        return refused
    try:
        status = agent_delivery.approve(delivery_id, user_email)
    except agent_delivery.DeliveryNotPending as exc:
        return not_pending(exc)
    return {"id": delivery_id, "status": status, "approved_by": user_email}


@router.post("/api/agents/deliveries/{delivery_id}/reject", dependencies=[Depends(same_origin)])
def reject_delivery(delivery_id: int, user_email: str = Depends(get_current_user)):
    if refused := reviewed(delivery_id, user_email):
        return refused
    try:
        agent_delivery.reject(delivery_id, user_email)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    logger.info("agent envoi %s refusé à la relecture", delivery_id)
    return {"id": delivery_id, "status": "rejected"}
