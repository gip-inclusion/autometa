"""Preuve déterministe (DOD-2) — l'artefact sonore de la notification existe et est un WAV valide."""

from pathlib import Path

SOUND = Path("web/static/sounds/notification.wav")


def test_dod_2_le_son_de_notification_est_un_wav_valide():
    data = SOUND.read_bytes()
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"
    assert len(data) > 44
