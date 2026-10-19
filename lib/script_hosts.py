"""Sites d'où une page de TDB peut charger un script — stdlib seule, pour que les hooks de garde puissent le lire."""

import re
from urllib.parse import urlsplit

# Why: sites mesurés le 19/10 sur les pages des TDB actifs (docs/audits/sujets/09). jsDelivr limité à
# /npm/ : /gh/ sert n'importe quel dépôt GitHub. La CSP (web/csp.py) et les contrôles à l'écriture
# lisent cette même liste : un site ajouté ici est autorisé partout à la fois.
ALLOWED = (
    "https://cdn.jsdelivr.net/npm/",
    "https://unpkg.com",
    "https://d3js.org",
    "https://matomo.inclusion.gouv.fr",
)

SCRIPT_SRC = re.compile(r"""<script\b[^>]*?\bsrc\s*=\s*["']?([^"'\s>]+)""", re.IGNORECASE)


def is_allowed(src: str) -> bool:
    url = urlsplit(src)
    if not url.scheme and not url.netloc:
        return True
    target = f"{url.scheme or 'https'}://{url.netloc.lower()}{url.path}"
    return target.startswith(tuple(site.rstrip("/") + "/" for site in ALLOWED))


def script_host_violations(html: str) -> list[str]:
    """Scripts d'une page qui viennent d'un site hors liste : le navigateur les refuserait."""
    return sorted({src for src in SCRIPT_SRC.findall(html) if not is_allowed(src)})
