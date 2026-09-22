"""Fenêtres de limite d'usage des moteurs d'agent, partagées par tous les workers via Redis."""

import argparse
import logging

import redis

from web import config

logger = logging.getLogger(__name__)


def limit_key(backend: str) -> str:
    return f"autometa:limit:{backend}"


def backend_is_limited(backend: str) -> bool:
    """Le moteur est dans sa fenêtre de limite d'usage — l'appeler ne ferait qu'attendre les retries."""
    # Why: client synchrone jetable — ces appels partent de threads démons sans boucle asyncio,
    # et emprunter le pool async du runner depuis une autre boucle le corromprait.
    try:
        with redis.Redis.from_url(config.REDIS_URL, decode_responses=True) as client:
            return bool(client.exists(limit_key(backend)))
    except redis.RedisError as exc:
        logger.warning("Lecture de l'état de limite impossible pour %s : %s", backend, exc)
        return False


def main(argv: list[str] | None = None) -> None:
    """Simule ou lève la limite d'un moteur, pour tester la bascule ou sortir d'un faux positif."""
    parser = argparse.ArgumentParser(prog="python -m web.engine_limits")
    parser.add_argument("action", choices=("simulate", "clear"))
    parser.add_argument("backend")
    parser.add_argument("--seconds", type=int, default=600)
    args = parser.parse_args(argv)
    with redis.Redis.from_url(config.REDIS_URL, decode_responses=True) as client:
        if args.action == "simulate":
            client.set(limit_key(args.backend), "1", ex=args.seconds)
        else:
            client.delete(limit_key(args.backend))


if __name__ == "__main__":
    main()
