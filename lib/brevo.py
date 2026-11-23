"""Client Brevo en lecture seule : modèles, campagnes et volumes d'envoi, jamais les contacts."""

import logging
from collections import defaultdict
from typing import Any, Optional

import httpx

from lib.api_signals import emit_api_signal
from lib.pii import EMAIL
from lib.sources import get_default_instance, get_source_config, list_instances

logger = logging.getLogger(__name__)

# Why: aucune route de contacts ou de listes n'est appelée, chaque réponse est réduite à une liste blanche de
# champs, et les événements d'envoi, qui portent l'adresse du destinataire, ne sortent qu'agrégés par modèle.
BASE_URL = "https://api.brevo.com/v3"
DEFAULT_TIMEOUT = 30
EVENT_PAGE = 5000
# Garde-fous anti-emballement : 20 pages de chaque route, soit 100 000 événements d'envoi au plus.
MAX_PAGES = 20
MAX_DAYS = 90  # limite de l'API Brevo pour les événements


class BrevoError(Exception):
    """Erreur d'appel à l'API Brevo."""


class BrevoInvalidRequest(BrevoError):
    """Requête refusée avant l'appel : méthode, paramètre ou valeur inconnus."""


def _template(t: dict, with_content: bool) -> dict:
    out = {
        "id": t.get("id"),
        "name": _masked(t.get("name")),
        "subject": _masked(t.get("subject")),
        "isActive": t.get("isActive"),
        "tag": _masked(t.get("tag")),
        "sender": (t.get("sender") or {}).get("name"),
        "createdAt": t.get("createdAt"),
        "modifiedAt": t.get("modifiedAt"),
    }
    if with_content:
        out["htmlContent"] = _masked(t.get("htmlContent"))
    return out


def _masked(text: Optional[str]) -> Optional[str]:
    return EMAIL.sub("[adresse masquée]", text) if isinstance(text, str) else text


def _campaign(c: dict, with_content: bool) -> dict:
    stats = (c.get("statistics") or {}).get("globalStats") or {}
    out = {
        "id": c.get("id"),
        "name": _masked(c.get("name")),
        "subject": _masked(c.get("subject")),
        "previewText": _masked(c.get("previewText")),
        "status": c.get("status"),
        "type": c.get("type"),
        "tag": _masked(c.get("tag")),
        "sender": (c.get("sender") or {}).get("name"),
        "listIds": (c.get("recipients") or {}).get("lists") or [],
        "createdAt": c.get("createdAt"),
        "scheduledAt": c.get("scheduledAt"),
        "sentDate": c.get("sentDate"),
        "stats": {
            k: stats[k]
            for k in (
                "sent",
                "delivered",
                "uniqueViews",
                "uniqueClicks",
                "unsubscriptions",
                "hardBounces",
                "softBounces",
                "opensRate",
            )
            if k in stats
        },
    }
    if with_content:
        out["htmlContent"] = _masked(c.get("htmlContent"))
    return out


def _days(days: int) -> int:
    if not isinstance(days, int) or isinstance(days, bool):
        raise BrevoInvalidRequest(f"days doit être un entier, reçu {days!r}")
    return max(1, min(days, MAX_DAYS))


class BrevoClient:
    def __init__(self, instance: Optional[str] = None, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.instance = instance or get_default_instance("brevo")
        accounts = list_instances("brevo")
        if self.instance not in accounts:
            raise BrevoInvalidRequest(f"compte Brevo inconnu : {self.instance!r}. Comptes : {', '.join(accounts)}")
        if api_key is None:
            try:
                api_key = get_source_config("brevo", self.instance).get("api_key")
            except ValueError as e:
                raise BrevoError(f"Brevo {self.instance} : {e}") from e
        if not api_key:
            raise BrevoError(f"Brevo {self.instance} : clé absente")
        self.timeout = timeout
        self._session = httpx.Client(
            base_url=BASE_URL,
            headers={"api-key": api_key, "accept": "application/json"},
            transport=httpx.HTTPTransport(retries=2),
            timeout=timeout,
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        try:
            resp = self._session.get(path, params=params, timeout=httpx.Timeout(self.timeout, connect=10))
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
        except httpx.HTTPStatusError as e:
            raise BrevoError(f"Brevo {self.instance} GET {path} -> HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise BrevoError(f"Brevo {self.instance} GET {path} -> {e}") from e
        except ValueError as e:
            raise BrevoError(f"Brevo {self.instance} GET {path} -> réponse qui n'est pas du JSON") from e
        emit_api_signal(source="brevo", instance=self.instance, url=f"{BASE_URL}{path}", method=f"GET {path}")
        return data

    def _pages(self, path: str, key: str, size: int, params: dict) -> list[dict]:
        rows: list[dict] = []
        for page in range(MAX_PAGES):
            batch = self._get(path, {**params, "limit": size, "offset": page * size}).get(key) or []
            rows.extend(batch)
            if len(batch) < size:
                return rows
        logger.warning("brevo.pagination_cap", extra={"brevo.path": path, "brevo.rows": len(rows)})
        return rows

    def list_templates(self, with_content: bool = False) -> list[dict]:
        """Modèles d'email transactionnels du compte, actifs ou non."""
        return [_template(t, with_content) for t in self._pages("/smtp/templates", "templates", 1000, {})]

    def list_campaigns(self, status: Optional[str] = None, with_content: bool = False) -> list[dict]:
        """Campagnes du compte, les plus récentes d'abord, avec leurs statistiques globales."""
        params: dict[str, Any] = {
            "sort": "desc",
            "statistics": "globalStats",
            "excludeHtmlContent": "false" if with_content else "true",
        }
        if status:
            params["status"] = status
        return [_campaign(c, with_content) for c in self._pages("/emailCampaigns", "campaigns", 100, params)]

    def sends_by_template(self, days: int = 30) -> dict:
        """Demandes d'envoi par modèle sur les derniers jours. Ni adresse ni objet rendu d'un destinataire ne sort."""
        days = _days(days)
        counts: dict = defaultdict(lambda: {"count": 0, "lastDate": None})
        truncated = True
        for page in range(MAX_PAGES):
            params = {
                "event": "requests",
                "days": days,
                "sort": "desc",
                "limit": EVENT_PAGE,
                "offset": page * EVENT_PAGE,
            }
            batch = self._get("/smtp/statistics/events", params).get("events") or []
            for e in batch:
                # Why: l'objet rendu d'un modèle peut porter une donnée du destinataire ; on ne garde que son
                # identifiant, et l'objet du modèle se lit par `templates`. Un email sans modèle n'a que son objet.
                tid = e.get("templateId")
                row = counts[(tid, None) if tid is not None else (None, e.get("subject"))]
                row["count"] += 1
                # Tri décroissant : le premier événement vu est le plus récent.
                row["lastDate"] = row["lastDate"] or e.get("date")
            if len(batch) < EVENT_PAGE:
                truncated = False
                break
        if truncated:
            logger.warning("brevo.events_cap", extra={"brevo.instance": self.instance, "brevo.days": days})
        templates, rare = [], {"templateId": None, "count": 0, "subject": None, "lastDate": None, "subjects": 0}
        for (tid, subject), row in counts.items():
            if tid is not None:
                templates.append({"templateId": tid, **row})
            # Why: un objet vu moins de 5 fois est personnalisé (nom de structure, parfois de personne) ; il
            # rejoint une ligne sans objet pour que la sortie ne cite personne.
            elif row["count"] >= 5 and not EMAIL.search(subject or ""):
                templates.append({
                    "templateId": None,
                    "count": row["count"],
                    "subject": subject,
                    "lastDate": row["lastDate"],
                })
            else:
                rare["count"] += row["count"]
                rare["subjects"] += 1
                rare["lastDate"] = max(filter(None, (rare["lastDate"], row["lastDate"])), default=None)
        if rare["count"]:
            templates.append(rare)
        templates.sort(key=lambda r: -r["count"])
        return {"days": days, "truncated": truncated, "templates": templates}


METHODS = {
    "templates": ("list_templates", {"with_content"}),
    "campaigns": ("list_campaigns", {"status", "with_content"}),
    "sends_by_template": ("sends_by_template", {"days"}),
}


def run(instance: str, method: str, params: Optional[dict] = None, timeout: int = DEFAULT_TIMEOUT) -> Any:
    """Point d'entrée commun de la façade et de /api/query : une méthode permise, des paramètres permis."""
    if not isinstance(method, str) or method not in METHODS:
        raise BrevoInvalidRequest(f"méthode Brevo inconnue : {method!r}. Valeurs : {', '.join(METHODS)}")
    name, allowed = METHODS[method]
    params = params or {}
    if not isinstance(params, dict):
        raise BrevoInvalidRequest(f"params doit être un objet, reçu {type(params).__name__}")
    unknown = set(params) - allowed
    if unknown:
        raise BrevoInvalidRequest(
            f"paramètres non permis pour {method} : {', '.join(sorted(unknown))}. "
            f"Paramètres permis : {', '.join(sorted(allowed))}"
        )
    if not isinstance(params.get("with_content", False), bool):
        raise BrevoInvalidRequest(f"with_content doit être un booléen, reçu {params['with_content']!r}")
    if not isinstance(params.get("status", ""), str):
        raise BrevoInvalidRequest(f"status doit être une chaîne, reçu {params['status']!r}")
    with BrevoClient(instance, timeout=timeout) as client:
        return getattr(client, name)(**params)
