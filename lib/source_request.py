"""Contrôle commun des requêtes adressées à une source en lecture, fait avant tout appel réseau."""

from typing import Any


class InvalidRequest(Exception):
    """Requête refusée avant l'appel : la faute est dans la requête, pas dans la source."""


def check_request(
    source: str,
    methods: dict[str, tuple[set[str], set[str]]],
    method: Any,
    params: Any,
    error: type[InvalidRequest] = InvalidRequest,
) -> dict:
    """Rend les paramètres d'une méthode permise ; sinon lève `error` en disant ce qui est permis."""
    if not isinstance(method, str) or method not in methods:
        raise error(f"méthode {source} inconnue : {method!r}. Valeurs : {', '.join(methods)}")
    required, optional = methods[method]
    params = params or {}
    if not isinstance(params, dict):
        raise error(f"params doit être un objet, reçu {type(params).__name__}")
    allowed = ", ".join([*sorted(required), *sorted(optional)]) or "aucun"
    if unknown := set(params) - required - optional:
        raise error(
            f"paramètres non permis pour {method} : {', '.join(sorted(unknown))}. Paramètres permis : {allowed}"
        )
    if missing := required - set(params):
        raise error(f"paramètres manquants pour {method} : {', '.join(sorted(missing))}. Paramètres permis : {allowed}")
    return params
