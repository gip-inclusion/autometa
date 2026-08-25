"""Per-user favorites — personal, never admin-gated (pins are the admin-facing gesture)."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from web.database import store
from web.deps import get_current_user

router = APIRouter(prefix="/api/favorites", tags=["favorites"])
logger = logging.getLogger(__name__)

ItemType = Literal["conversation", "report", "app"]


def item_exists(item_type: str, item_id: str) -> bool:
    if item_type == "conversation":
        return store.get_conversation(item_id, include_messages=False) is not None
    if item_type == "report":
        return item_id.isdigit() and store.get_report(int(item_id)) is not None
    dashboard = store.get_dashboard(item_id)
    return dashboard is not None and not dashboard["is_archived"]


@router.patch("/order")
async def reorder_favorites(request: Request, user_email: str = Depends(get_current_user)):
    try:
        data = await request.json()
        items = [(i["item_type"], str(i["item_id"])) for i in data["items"]]
    except ValueError, TypeError, KeyError:
        return JSONResponse({"error": "Invalid body"}, status_code=400)
    store.reorder_favorites(user_email, items)
    return {"ok": True}


@router.post("/{item_type}/{item_id}")
def add_favorite(item_type: ItemType, item_id: str, user_email: str = Depends(get_current_user)):
    if not item_exists(item_type, item_id):
        return JSONResponse({"error": "Item not found"}, status_code=404)
    try:
        store.add_favorite(user_email, item_type, item_id)
    except IntegrityError:
        # Why: le SELECT puis l'INSERT de add_favorite ne sont pas atomiques — un double-clic
        # concurrent viole l'unicité alors que le résultat voulu est déjà atteint.
        logger.debug("Concurrent favorite insert for %s/%s/%s", user_email, item_type, item_id)
    return {"ok": True}


@router.delete("/{item_type}/{item_id}")
def remove_favorite(item_type: ItemType, item_id: str, user_email: str = Depends(get_current_user)):
    store.remove_favorite(user_email, item_type, item_id)
    return {"ok": True}
