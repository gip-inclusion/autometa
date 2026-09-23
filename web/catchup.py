"""Rendu du message de rattrapage donné à un moteur qui reprend la main."""

import json

TOTAL_CAP = 30000

_KEPT_TYPES = ("user", "assistant", "tool_use", "tool_result")


def _clip(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return f"{text[:cap]}… [tronqué, {len(text)} caractères au total]"


def _render(msg) -> dict:
    if msg.type == "user":
        return {"role": "user", "content": msg.content}
    if msg.type == "assistant":
        return {"role": "assistant", "content": msg.content}

    try:
        payload = json.loads(msg.content)
        if not isinstance(payload, dict):
            payload = {}
    except json.JSONDecodeError, TypeError:
        payload = {}

    if msg.type == "tool_use":
        tool = payload.get("tool") or "outil"
        rendered = _clip(json.dumps(payload.get("input", {}), ensure_ascii=False), 300)
        return {"role": "assistant", "content": f"[appel {tool}] {rendered}"}

    output = payload.get("output", msg.content)
    if not isinstance(output, str):
        output = json.dumps(output, ensure_ascii=False)
    return {"role": "assistant", "content": f"[résultat] {_clip(output, 1000)}"}


def build_catchup(messages: list) -> list[dict]:
    """Ce qui s'est passé depuis qu'un moteur a parlé, borné en taille."""
    entries = [_render(m) for m in messages if m.type in _KEPT_TYPES]

    kept: list[dict] = []
    total = 0
    # Why: on garde la fin — le contexte le plus proche du tour à jouer est le plus utile.
    for entry in reversed(entries):
        size = len(entry["content"])
        if total + size > TOTAL_CAP:
            if not kept:
                # Why: même politique que la sélection des entrées — sur une entrée unique
                # surdimensionnée, c'est sa fin qui touche le tour à jouer.
                # Why: 50 laisse la place au préfixe « [tronqué, N caractères au total] … » ajouté ci-dessous.
                tail = entry["content"][-(TOTAL_CAP - 50) :]
                kept.append({"role": entry["role"], "content": f"[tronqué, {size} caractères au total] …{tail}"})
            break
        kept.append(entry)
        total += size
    return list(reversed(kept))
