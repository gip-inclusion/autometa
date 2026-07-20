"""Zendesk query scripts — re-exports of the lib client."""
from lib.sources import get_zendesk as load_api
from lib.zendesk import TicketResult, ZendeskAPI, ZendeskComment, ZendeskError, ZendeskTicket

__all__ = ["TicketResult", "ZendeskAPI", "ZendeskComment", "ZendeskError", "ZendeskTicket", "load_api"]
