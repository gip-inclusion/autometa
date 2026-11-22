"""Client Attio (CRM de l'équipe) — lecture des objets, enregistrements et listes (lecture seule, phase 1)."""

import logging
from typing import Any, Iterator, Optional

import httpx

from lib.api_signals import emit_api_signal
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
        emit_api_signal(source="attio", instance="default", url=f"{BASE_URL}{path}", method=f"{method} {path}")
        return data

    # Lecture seule : les seuls POST sont les routes de requête d'Attio (`/query`), qui n'écrivent rien.

    def list_objects(self) -> list[dict]:
        return self._call("GET", "/objects").get("data", [])

    def list_attributes(self, obj: str) -> list[dict]:
        return self._call("GET", f"/objects/{obj}/attributes").get("data", [])

    def list_options(self, obj: str, attribute: str) -> list[dict]:
        return self._call("GET", f"/objects/{obj}/attributes/{attribute}/options").get("data", [])

    def get_record(self, obj: str, record_id: str) -> dict:
        return self._call("GET", f"/objects/{obj}/records/{record_id}").get("data", {})

    def query_records(
        self,
        obj: str,
        *,
        filter: Optional[dict] = None,
        sorts: Optional[list] = None,
        limit: int = PAGE_SIZE,
        offset: int = 0,
    ) -> list[dict]:
        body: dict[str, Any] = {"limit": limit, "offset": offset}
        if filter:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts
        return self._call("POST", f"/objects/{obj}/records/query", json=body).get("data", [])

    def iter_records(
        self, obj: str, *, filter: Optional[dict] = None, sorts: Optional[list] = None, max_pages: int = MAX_PAGES
    ) -> Iterator[dict]:
        """Itère les enregistrements par pages de 500, plafonné à `max_pages`."""
        for page in range(max_pages):
            rows = self.query_records(obj, filter=filter, sorts=sorts, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
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
    """Réduit une valeur Attio à ce qu'un humain lit (nom, email, libellé d'option, identifiant lié...)."""
    t = v.get("attribute_type")
    if t == "personal-name":
        return v.get("full_name")
    if t == "email-address":
        return v.get("email_address")
    if t == "domain":
        return v.get("domain")
    if t == "phone-number":
        return v.get("original_phone_number")
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


COORDONNEES = ("email-address", "phone-number")


def aplatir(record: dict, champs: Optional[list[str]] = None, sans_coordonnees: bool = False) -> dict:
    """Un enregistrement (ou une entrée de liste) en dictionnaire simple : {id, champ: valeur ou liste de valeurs}.

    `sans_coordonnees` retire les emails et les téléphones : c'est le cas de tout ce qui sort par `run()`.
    """
    valeurs = record.get("values") or record.get("entry_values") or {}
    rid = record.get("id", {})
    out: dict[str, Any] = {"id": rid.get("record_id") or rid.get("entry_id")}
    if "parent_record_id" in record:
        out["parent_record_id"] = record["parent_record_id"]
    for slug, vs in valeurs.items():
        if champs and slug not in champs:
            continue
        if sans_coordonnees:
            vs = [v for v in vs or [] if v.get("attribute_type") not in COORDONNEES]
        lues = [x for x in (_valeur(v) for v in vs or []) if x not in (None, "")]
        if lues:
            out[slug] = lues[0] if len(lues) == 1 else lues
    return out


class AttioInvalidRequest(AttioError):
    """Requête refusée avant l'appel : méthode ou paramètre inconnus."""


def _compter(rows: list[dict], par: Optional[str]) -> dict:
    out: dict = {"total": len(rows)}
    if par:
        counts: dict = {}
        for r in rows:
            v = r.get(par)
            for x in v if isinstance(v, list) else [v]:
                key = x if x is not None else "(vide)"
                counts[key] = counts.get(key, 0) + 1
        out["par_" + par] = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    return out


def _objects(c: AttioClient) -> list[dict]:
    return [{"slug": o.get("api_slug"), "nom": o.get("plural_noun")} for o in c.list_objects()]


def _attributes(c: AttioClient, object: str) -> list[dict]:
    return [
        {"slug": a.get("api_slug"), "nom": a.get("title"), "type": a.get("type"), "multiple": a.get("is_multiselect")}
        for a in c.list_attributes(object)
        if not a.get("is_archived")
    ]


def _options(c: AttioClient, object: str, attribute: str) -> list[str]:
    return [o.get("title") for o in c.list_options(object, attribute) if not o.get("is_archived")]


def _limit(limit: Any) -> int:
    try:
        return max(1, min(int(limit), PAGE_SIZE))
    except (TypeError, ValueError) as e:
        raise AttioInvalidRequest(f"limit doit être un entier, reçu {limit!r}") from e


def _records(
    c: AttioClient, object: str, filter: Optional[dict] = None, fields: Optional[list] = None, limit: int = 50
) -> list[dict]:
    rows = c.query_records(object, filter=filter, limit=_limit(limit))
    return [aplatir(r, fields, sans_coordonnees=True) for r in rows]


def _count(c: AttioClient, object: str, filter: Optional[dict] = None, by: Optional[str] = None) -> dict:
    rows = [aplatir(r, [by] if by else ["id"], sans_coordonnees=True) for r in c.iter_records(object, filter=filter)]
    return _compter(rows, by)


def _lists(c: AttioClient) -> list[dict]:
    return [
        {
            "slug": x.get("api_slug"),
            "nom": x.get("name"),
            "objet": (x.get("parent_object") or [None])[0],
            "id": (x.get("id") or {}).get("list_id"),
        }
        for x in c.list_lists()
    ]


def _entries(c: AttioClient, list: str, filter: Optional[dict] = None, fields: Optional[Any] = None) -> Any:
    return [aplatir(e, fields, sans_coordonnees=True) for e in c.iter_entries(list, filter=filter)]


# Méthodes permises : fonction, paramètres obligatoires, paramètres facultatifs. Aucune n'écrit dans le CRM.
METHODS = {
    "objects": (_objects, set(), set()),
    "attributes": (_attributes, {"object"}, set()),
    "options": (_options, {"object", "attribute"}, set()),
    "records": (_records, {"object"}, {"filter", "fields", "limit"}),
    "count": (_count, {"object"}, {"filter", "by"}),
    "lists": (_lists, set(), set()),
    "entries": (_entries, {"list"}, {"filter", "fields"}),
}


def run(method: str, params: Optional[dict] = None, timeout: int = DEFAULT_TIMEOUT) -> Any:
    """Point d'entrée commun de la façade et de /api/query : une méthode permise, des paramètres permis."""
    if method not in METHODS:
        raise AttioInvalidRequest(f"méthode Attio inconnue : {method}. Valeurs : {', '.join(METHODS)}")
    fn, required, optional = METHODS[method]
    params = params or {}
    unknown = set(params) - required - optional
    if unknown:
        raise AttioInvalidRequest(f"paramètres non permis pour {method} : {', '.join(sorted(unknown))}")
    missing = required - set(params)
    if missing:
        raise AttioInvalidRequest(f"paramètres manquants pour {method} : {', '.join(sorted(missing))}")
    with AttioClient(timeout=timeout) as client:
        return fn(client, **params)
