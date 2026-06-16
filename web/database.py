"""Facade for the domain store mixins — keeps the historical `web.database` import surface."""

from web.db import get_db
from web.stores.conversations import ConversationsMixin
from web.stores.dashboards import DashboardsMixin
from web.stores.files import FilesMixin
from web.stores.pins import PinsMixin
from web.stores.records import (
    VALID_CONVERSATION_COLUMNS,
    VALID_REPORT_COLUMNS,
    Conversation,
    Message,
    PinnedItem,
    Report,
    Tag,
    UploadedFile,
    build_update_clause,
)
from web.stores.reports import ReportsMixin
from web.stores.tags import TagsMixin

__all__ = [
    "VALID_CONVERSATION_COLUMNS",
    "VALID_REPORT_COLUMNS",
    "Conversation",
    "ConversationStore",
    "LazyConversationStore",
    "Message",
    "PinnedItem",
    "Report",
    "Tag",
    "UploadedFile",
    "build_update_clause",
    "get_db",
    "store",
]


class ConversationStore(ConversationsMixin, PinsMixin, ReportsMixin, DashboardsMixin, TagsMixin, FilesMixin):
    """PostgreSQL-backed conversation and report store."""


class LazyConversationStore:
    _store = None

    def __getattr__(self, name):
        if LazyConversationStore._store is None:
            LazyConversationStore._store = ConversationStore()
        return getattr(LazyConversationStore._store, name)


store = LazyConversationStore()
