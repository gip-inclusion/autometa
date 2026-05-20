"""Per-request correlation IDs. Backs structured logs and trace tags."""

import uuid
from contextvars import ContextVar

import sentry_sdk
from fastapi import Request

REQUEST_ID_HEADER = "X-Request-ID"

current_request_id: ContextVar[str | None] = ContextVar("autometa_request_id", default=None)
current_conversation_id: ContextVar[str | None] = ContextVar("autometa_conversation_id", default=None)
current_user_id: ContextVar[str | None] = ContextVar("autometa_user_id", default=None)
current_client_ip: ContextVar[str | None] = ContextVar("autometa_client_ip", default=None)


def set_conversation_id(conversation_id: str | None) -> None:
    """Bind a conversation id to the current context — picked up by log filter and Sentry."""
    current_conversation_id.set(conversation_id)
    if conversation_id:
        sentry_sdk.set_tag("conversation_id", conversation_id)


async def request_id_middleware(request: Request, call_next):
    """Bind request_id, user_id and client_ip to context for log correlation."""
    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
    req_tok = current_request_id.set(request_id)
    user_tok = current_user_id.set(request.headers.get("X-Forwarded-User"))
    ip_tok = current_client_ip.set(request.client.host if request.client else None)
    sentry_sdk.set_tag("request_id", request_id)
    try:
        response = await call_next(request)
    finally:
        current_request_id.reset(req_tok)
        current_user_id.reset(user_tok)
        current_client_ip.reset(ip_tok)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
