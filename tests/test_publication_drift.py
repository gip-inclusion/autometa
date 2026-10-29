from datetime import datetime, timedelta, timezone

from web.publications import drifted_environments

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _pub(environment, published_at, **extra):
    return {"environment": environment, "published_at": published_at, **extra}


def test_dod_1_une_version_en_retard_est_signalee_meme_si_une_autre_est_a_jour():
    updated = EPOCH + timedelta(days=2)
    pubs = [
        _pub("staging", EPOCH),
        _pub("production", EPOCH + timedelta(days=3)),
    ]
    assert drifted_environments(pubs, updated) == ["staging"]


def test_dod_4_republier_cree_une_version_a_jour_qui_efface_le_retard():
    updated = EPOCH + timedelta(days=2)
    pubs = [
        _pub("staging", EPOCH),
        _pub("staging", EPOCH + timedelta(days=5)),
    ]
    assert drifted_environments(pubs, updated) == []


def test_dod_5_aucune_version_en_ligne_ne_signale_rien():
    assert drifted_environments([], EPOCH) == []


def test_dod_6_toutes_les_versions_a_jour_ne_signalent_rien():
    pubs = [
        _pub("staging", EPOCH + timedelta(days=1)),
        _pub("production", EPOCH + timedelta(days=1)),
    ]
    assert drifted_environments(pubs, EPOCH) == []


def test_dod_9_un_rafraichissement_ne_leve_pas_le_retard():
    updated = EPOCH + timedelta(days=2)
    pubs = [_pub("production", EPOCH, last_successful_refresh_at=EPOCH + timedelta(days=10))]
    assert drifted_environments(pubs, updated) == ["production"]
