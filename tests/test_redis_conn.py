"""Réglages du pool Redis partagé."""

import asyncio
import socket

from web.redis_conn import get_redis


def test_pooled_connections_detect_a_vanished_peer(mocker):
    """Le keepalive TCP fait tomber une connexion dont le pair a disparu, même sans rien écrire."""
    mocker.patch("web.redis_conn._pool", None)

    kwargs = asyncio.run(get_redis()).connection_pool.connection_kwargs

    assert kwargs["socket_keepalive"] is True
    assert kwargs["socket_keepalive_options"]


def test_keepalive_idle_falls_back_to_the_macos_name(mocker, monkeypatch):
    mocker.patch("web.redis_conn._pool", None)
    monkeypatch.delattr(socket, "TCP_KEEPIDLE", raising=False)
    monkeypatch.setattr(socket, "TCP_KEEPALIVE", 0x10, raising=False)

    kwargs = asyncio.run(get_redis()).connection_pool.connection_kwargs

    assert kwargs["socket_keepalive_options"][0x10] == 30
