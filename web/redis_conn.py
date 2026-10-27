"""Redis async connection pool."""

import socket

import redis.asyncio as aioredis

from . import config

# Why: sans délai, une lecture sur une connexion muette attend sans fin. Doit dépasser le délai
# serveur du BLPOP du runner (1 s).
SOCKET_TIMEOUT = 5

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is not None:
        try:
            await _pool.ping()
        except aioredis.ConnectionError, aioredis.TimeoutError, RuntimeError, OSError:
            _pool = None
    if _pool is None:
        # Why: un abonnement n'écrit jamais ; sans keepalive TCP, une connexion dont le pair a disparu
        # reste ouverte sans erreur et l'écoute de l'arrêt devient sourde. Panne vue en une minute environ.
        _pool = aioredis.from_url(
            config.REDIS_URL,
            decode_responses=True,
            socket_timeout=SOCKET_TIMEOUT,
            socket_keepalive=True,
            socket_keepalive_options={socket.TCP_KEEPIDLE: 30, socket.TCP_KEEPINTVL: 10, socket.TCP_KEEPCNT: 3},
        )
    return _pool


async def close_redis():
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
