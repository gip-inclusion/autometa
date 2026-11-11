"""Preparation url: a public https page or file, as text; Autometa fetches it, never a private address."""

import ipaddress
import re
import socket
from urllib.parse import urlsplit

import httpx

DESCRIPTION = "une page ou un fichier texte public en https (HTML rendu en texte)"
FIELDS = {"url": "obligatoire, une adresse https publique"}
TEXT_TYPES = ("text/", "application/json", "application/xml")


def errors(step: dict) -> list[str]:
    url = step.get("url")
    parts = urlsplit(url) if isinstance(url, str) else None
    if not (parts and len(url) <= 2000 and parts.scheme == "https" and parts.hostname and "@" not in parts.netloc):
        return ["url : attendu une adresse https:// sans identifiants."]
    return []


def source(step: dict) -> str:
    return step["url"]


def public_address(host: str) -> str | None:
    """The address to connect to, only when every address of the host is public; None otherwise."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return None
    addresses = [ipaddress.ip_address(info[4][0]) for info in infos]
    return str(addresses[0]) if addresses and all(a.is_global for a in addresses) else None


def pinned(url: str, address: str) -> str:
    parts = urlsplit(url)
    netloc = f"[{address}]" if ":" in address else address
    return parts._replace(netloc=netloc + (f":{parts.port}" if parts.port else "")).geturl()


def html_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|section|article)>", "\n", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return "\n".join(line for line in (re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()) if line)


def client() -> httpx.Client:
    return httpx.Client(timeout=30, follow_redirects=False)


def read(url: str, address: str, limit: int) -> tuple[str, str]:
    """The text of a public page, read from the checked address, refused beyond limit bytes."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    with client() as session:
        # Why: the connection goes to the address checked, never to a second resolution of the name (DNS
        # rebinding); Host and SNI keep the name, so the certificate is still verified against it.
        request = session.build_request(
            "GET",
            pinned(url, address),
            headers={"Host": host + (f":{parts.port}" if parts.port else "")},
            extensions={"sni_hostname": host},
        )
        resp = session.send(request, stream=True)
        try:
            resp.raise_for_status()
            kind = resp.headers.get("content-type", "")
            if not kind.startswith(TEXT_TYPES):
                raise ValueError(f"préparation url {host} : contenu {kind or 'inconnu'}, seul le texte est lu")
            too_big = ValueError(f"préparation url {host} : réponse de plus de {limit} octets, rien n'est lu")
            if int(resp.headers.get("content-length") or 0) > limit:
                raise too_big
            body = bytearray()
            for chunk in resp.iter_bytes():
                body += chunk
                if len(body) > limit:
                    raise too_big
        finally:
            resp.close()
    return kind, body.decode(resp.encoding or "utf-8", errors="replace")


def prepare(step: dict, cap: int, cursor: int) -> dict:
    host = urlsplit(step["url"]).hostname or ""
    if not (address := public_address(host)):
        raise ValueError(f"préparation url : {host} ne résout pas vers une adresse publique, le run n'est pas lancé")
    # Why: HTML weighs up to about ten times its text; beyond that, the page cannot fit the cap anyway.
    limit = 10 * cap
    try:
        kind, text = read(step["url"], address, limit)
    except httpx.HTTPError as exc:
        raise ValueError(f"préparation url {host} : lecture impossible ({exc})") from exc
    return {"content": html_text(text) if "html" in kind else text}
