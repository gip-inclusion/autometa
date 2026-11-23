"""Client Attio (CRM de l'équipe) en lecture seule : objets, enregistrements et listes."""

import json
import logging
import re
from typing import Any, Iterator, Optional

import httpx

from lib.api_signals import emit_api_signal
from lib.pii import EMAIL
from web import config

logger = logging.getLogger(__name__)

BASE_URL = "https://api.attio.com/v2"
DEFAULT_TIMEOUT = 30
PAGE_SIZE = 500
# Garde-fou anti-emballement : 40 × 500 = 20 000 enregistrements avant arrêt + avertissement.
MAX_PAGES = 40


class AttioError(Exception):
    """Erreur d'appel à l'API Attio."""


class AttioClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.api_key = api_key or config.ATTIO_API_KEY
        if not self.api_key:
            raise AttioError("ATTIO_API_KEY not set")
        self.timeout = timeout
        self._session = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            transport=httpx.HTTPTransport(retries=2),
            timeout=timeout,
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _call(self, method: str, path: str, json: Optional[dict] = None) -> Any:
        try:
            resp = self._session.request(method, path, json=json, timeout=httpx.Timeout(self.timeout, connect=10))
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise AttioError(f"Attio {method} {path} -> HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise AttioError(f"Attio {method} {path} -> {e}") from e
        except ValueError as e:
            raise AttioError(f"Attio {method} {path} -> réponse illisible") from e
        emit_api_signal(source="attio", instance="default", url=f"{BASE_URL}{path}", method=f"{method} {path}")
        return data

    # Lecture seule : les seuls POST sont les routes de requête d'Attio (`/query`), qui n'écrivent rien.

    def list_objects(self) -> list[dict]:
        return self._call("GET", "/objects").get("data", [])

    def list_attributes(self, obj: str) -> list[dict]:
        return self._call("GET", f"/objects/{obj}/attributes").get("data", [])

    def list_options(self, obj: str, attribute: str) -> list[dict]:
        return self._call("GET", f"/objects/{obj}/attributes/{attribute}/options").get("data", [])

    def query_records(
        self, obj: str, *, filter: Optional[dict] = None, limit: int = PAGE_SIZE, offset: int = 0
    ) -> list[dict]:
        body: dict[str, Any] = {"limit": limit, "offset": offset}
        if filter:
            body["filter"] = filter
        return self._call("POST", f"/objects/{obj}/records/query", json=body).get("data", [])

    def iter_records(self, obj: str, *, filter: Optional[dict] = None, max_pages: int = MAX_PAGES) -> Iterator[dict]:
        """Itère les enregistrements par pages de 500, plafonné à `max_pages`."""
        for page in range(max_pages):
            rows = self.query_records(obj, filter=filter, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
            yield from rows
            if len(rows) < PAGE_SIZE:
                return
        logger.warning("Attio: pagination plafonnée à %d pages pour %s", max_pages, obj)

    def list_lists(self) -> list[dict]:
        return self._call("GET", "/lists").get("data", [])

    def iter_entries(
        self, list_id: str, *, filter: Optional[dict] = None, max_pages: int = MAX_PAGES
    ) -> Iterator[dict]:
        for page in range(max_pages):
            body: dict[str, Any] = {"limit": PAGE_SIZE, "offset": page * PAGE_SIZE}
            if filter:
                body["filter"] = filter
            rows = self._call("POST", f"/lists/{list_id}/entries/query", json=body).get("data", [])
            yield from rows
            if len(rows) < PAGE_SIZE:
                return
        logger.warning("Attio: pagination plafonnée à %d pages pour la liste %s", max_pages, list_id)


def _valeur(v: dict) -> Any:
    """Réduit une valeur Attio à ce qu'un humain lit (nom, libellé d'option, identifiant lié...)."""
    t = v.get("attribute_type")
    if t == "personal-name":
        return v.get("full_name")
    if t == "domain":
        return v.get("domain")
    if t == "select":
        return (v.get("option") or {}).get("title")
    if t == "status":
        return (v.get("status") or {}).get("title")
    if t == "record-reference":
        return v.get("target_record_id")
    if t == "actor-reference":
        return v.get("referenced_actor_id")
    if t == "interaction":
        return v.get("interacted_at")
    if t == "location":
        return ", ".join(x for x in (v.get("locality"), v.get("region"), v.get("country_code")) if x) or None
    if t == "currency":
        return v.get("currency_value")
    return v.get("value")


# Numéros français, avec ou sans +33 et séparateurs : les seuls qu'on trouve dans ce CRM.
PHONE = re.compile(r"(?:\+33\s?|\b0)[1-9](?:[\s.-]?\d{2}){4}\b")


def _lisible(v: dict) -> Any:
    """La valeur lue, sauf un email ou un téléphone, déclaré comme tel ou saisi dans un texte."""
    if v.get("attribute_type") in ("email-address", "phone-number"):
        return None
    x = _valeur(v)
    return None if isinstance(x, str) and (EMAIL.search(x) or PHONE.search(x)) else x


def aplatir(record: dict, champs: Optional[list[str]] = None) -> dict:
    """Un enregistrement (ou une entrée de liste) en {id, champ: valeur ou liste de valeurs}, sans email ni téléphone."""
    valeurs = record.get("values") or record.get("entry_values") or {}
    rid = record.get("id", {})
    out: dict[str, Any] = {"id": rid.get("record_id") or rid.get("entry_id")}
    if "parent_record_id" in record:
        out["parent_record_id"] = record["parent_record_id"]
    for slug, vs in valeurs.items():
        if champs and slug not in champs:
            continue
        lues = [x for x in (_lisible(v) for v in vs or []) if x not in (None, "")]
        if lues:
            out[slug] = lues[0] if len(lues) == 1 else lues
    return out


class AttioInvalidRequest(AttioError):
    """Requête refusée avant l'appel : méthode, paramètre ou valeur non permis."""


def _compter(rows: list[dict], par: Optional[str], complete: bool) -> dict:
    out: dict = {"total": len(rows), "complete": complete}
    if par:
        counts: dict = {}
        for r in rows:
            v = r.get(par)
            for x in v if isinstance(v, list) else [v]:
                key = x
                counts[key] = counts.get(key, 0) + 1
        out["by_" + par] = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    return out


def _objects(c: AttioClient) -> list[dict]:
    return [{"slug": o.get("api_slug"), "name": o.get("plural_noun")} for o in c.list_objects()]


def _attributes(c: AttioClient, object: str) -> list[dict]:
    return [
        {"slug": a.get("api_slug"), "name": a.get("title"), "type": a.get("type"), "multiple": a.get("is_multiselect")}
        for a in c.list_attributes(object)
        if not a.get("is_archived")
    ]


def _options(c: AttioClient, object: str, attribute: str) -> list[str]:
    return [o.get("title") for o in c.list_options(object, attribute) if not o.get("is_archived")]


def _records(
    c: AttioClient, object: str, filter: Optional[dict] = None, fields: Optional[list] = None, limit: int = 50
) -> list[dict]:
    return [aplatir(r, fields) for r in c.query_records(object, filter=filter, limit=max(1, min(limit, PAGE_SIZE)))]


def _count(c: AttioClient, object: str, filter: Optional[dict] = None, by: Optional[str] = None) -> dict:
    rows = [aplatir(r, [by] if by else ["id"]) for r in c.iter_records(object, filter=filter, max_pages=MAX_PAGES)]
    # Why: au plafond de pages, le total est un minimum ; `complete` le dit à l'agent et au tableau.
    return _compter(rows, by, complete=len(rows) < MAX_PAGES * PAGE_SIZE)


def _lists(c: AttioClient) -> list[dict]:
    return [
        {
            "slug": x.get("api_slug"),
            "name": x.get("name"),
            "object": (x.get("parent_object") or [None])[0],
            "id": (x.get("id") or {}).get("list_id"),
        }
        for x in c.list_lists()
    ]


def _entries(c: AttioClient, list: str, filter: Optional[dict] = None, fields: Optional[Any] = None) -> Any:
    return [aplatir(e, fields) for e in c.iter_entries(list, filter=filter)]


METHODS = {
    "objects": (_objects, set(), set()),
    "attributes": (_attributes, {"object"}, set()),
    "options": (_options, {"object", "attribute"}, set()),
    "records": (_records, {"object"}, {"filter", "fields", "limit"}),
    "count": (_count, {"object"}, {"filter", "by"}),
    "lists": (_lists, set(), set()),
    "entries": (_entries, {"list"}, {"filter", "fields"}),
}


# Why: `object`, `attribute` et `list` entrent dans le chemin de l'URL ; un `/` ou un `?` y viserait une autre
# route d'Attio, écriture comprise. Un slug ou un identifiant n'a ni l'un ni l'autre.
SLUG = re.compile(r"[A-Za-z0-9_-]{1,64}")
SLUG_TEXT = "un slug ou un identifiant (lettres, chiffres, _ et -)"
EXPECTED = {
    "object": (str, SLUG_TEXT),
    "attribute": (str, SLUG_TEXT),
    "list": (str, SLUG_TEXT),
    "by": (str, "un nom d'attribut"),
    "filter": (dict, "un objet JSON au format des filtres Attio"),
    "fields": (list, "une liste de noms d'attributs"),
    "limit": (int, "un entier"),
}


def _check(params: dict) -> None:
    for name, value in params.items():
        if value is None:
            continue
        kind, text = EXPECTED[name]
        valid = isinstance(value, kind) and not isinstance(value, bool)
        if valid and name in ("object", "attribute", "list"):
            valid = SLUG.fullmatch(value) is not None
        if valid and name == "fields":
            valid = all(isinstance(f, str) for f in value)
        if not valid:
            raise AttioInvalidRequest(f"{name} doit être {text}, reçu {value!r}")
        # Why: filtrer sur un email ou un téléphone dirait, par un total de 0 ou 1, si cette personne est dans le CRM.
        if name == "filter" and re.search(r"email_addresses|phone_numbers|@|\+33", json.dumps(value)):
            raise AttioInvalidRequest("un filtre ne porte ni sur un email ni sur un téléphone")


def run(method: str, params: Optional[dict] = None, timeout: int = DEFAULT_TIMEOUT) -> Any:
    """Point d'entrée commun de la façade et de /api/query : une méthode permise, des paramètres permis."""
    if not isinstance(method, str) or method not in METHODS:
        raise AttioInvalidRequest(f"méthode Attio inconnue : {method!r}. Valeurs : {', '.join(METHODS)}")
    fn, required, optional = METHODS[method]
    params = params or {}
    if not isinstance(params, dict):
        raise AttioInvalidRequest(f"params doit être un objet, reçu {type(params).__name__}")
    allowed = ", ".join([*sorted(required), *sorted(optional)]) or "aucun"
    if unknown := set(params) - required - optional:
        raise AttioInvalidRequest(
            f"paramètres non permis pour {method} : {', '.join(sorted(unknown))}. Paramètres permis : {allowed}"
        )
    if missing := required - set(params):
        raise AttioInvalidRequest(
            f"paramètres manquants pour {method} : {', '.join(sorted(missing))}. Paramètres permis : {allowed}"
        )
    _check(params)
    with AttioClient(timeout=timeout) as client:
        return fn(client, **params)
