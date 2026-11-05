"""Preparation url: a public https page or file, as text; Autometa fetches it, never a private address."""

import ipaddress
import re
import socket
from urllib.parse import urlsplit

import httpx

DESCRIPTION = "une page ou un fichier texte public en https (HTML rendu en texte)"
CHAMPS = {"url": "obligatoire, une adresse https publique"}
TEXT_TYPES = ("text/", "application/json", "application/xml")


def errors(step: dict) -> list[str]:
    url = step.get("url")
    if not (isinstance(url, str) and len(url) <= 2000 and urlsplit(url).scheme == "https" and urlsplit(url).hostname):
        return ["url : attendu une adresse https://."]
    return []


def source(step: dict) -> str:
    return step["url"]


def public_host(host: str) -> bool:
    """Why: Autometa fetches from inside its network; an internal or metadata address must stay unreachable."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False
    return all(ipaddress.ip_address(info[4][0]).is_global for info in infos)


def html_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|section|article)>", "\n", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return "\n".join(line for line in (re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()) if line)


def prepare(step: dict, plafond: int, debut: int) -> dict:
    host = urlsplit(step["url"]).hostname or ""
    if not public_host(host):
        raise ValueError(f"préparation url : {host} ne résout pas vers une adresse publique, le run n'est pas lancé")
    try:
        resp = httpx.get(step["url"], timeout=30, follow_redirects=False)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise ValueError(f"préparation url {host} : lecture impossible ({exc})") from exc
    kind = resp.headers.get("content-type", "")
    if not kind.startswith(TEXT_TYPES):
        raise ValueError(f"préparation url {host} : contenu {kind or 'inconnu'}, seul le texte est lu")
    return {"contenu": html_text(resp.text) if "html" in kind else resp.text}
