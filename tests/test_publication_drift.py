from web.publications import drifted_environments, snapshot_drifted


def _pub(environment, publication_id):
    return {"environment": environment, "publication_id": publication_id}


def test_dod_1_une_version_en_retard_est_signalee_meme_si_une_autre_est_a_jour(mocker):
    mocker.patch("web.publications.snapshot_drifted", side_effect=lambda slug, pid: pid == "stg")
    pubs = [_pub("production", "prod"), _pub("staging", "stg")]
    assert drifted_environments("d", pubs) == ["staging"]


def test_ordre_staging_avant_production_quand_les_deux_derivent(mocker):
    mocker.patch("web.publications.snapshot_drifted", return_value=True)
    pubs = [_pub("production", "prod"), _pub("staging", "stg")]
    assert drifted_environments("d", pubs) == ["staging", "production"]


def test_dod_4_la_publication_active_a_jour_efface_le_retard(mocker):
    # La plus récente (active) est à jour ; une ancienne version staging figée est ignorée.
    mocker.patch("web.publications.snapshot_drifted", side_effect=lambda slug, pid: pid == "old")
    pubs = [_pub("staging", "new"), _pub("staging", "old")]
    assert drifted_environments("d", pubs) == []


def test_dod_5_aucune_version_en_ligne_ne_signale_rien(mocker):
    drift = mocker.patch("web.publications.snapshot_drifted")
    assert drifted_environments("d", []) == []
    drift.assert_not_called()


def test_dod_6_toutes_les_versions_a_jour_ne_signalent_rien(mocker):
    mocker.patch("web.publications.snapshot_drifted", return_value=False)
    pubs = [_pub("staging", "stg"), _pub("production", "prod")]
    assert drifted_environments("d", pubs) == []


def test_dod_9_les_donnees_reecrites_par_le_cron_ne_font_pas_un_retard(mocker):
    def etags(bucket, prefix):
        source = {"index.html": "a", "app.js": "b"}
        if prefix.startswith("interactive/"):
            return {**source, "data.json": "frais", "data/bas-rhin.json": "frais"}
        return {**source, "data.json": "figé", "data/bas-rhin.json": "figé"}

    mocker.patch("web.publications.s3.etags_under", side_effect=etags)
    assert snapshot_drifted("d", "pub") is False


def test_une_modification_de_fichier_source_est_un_retard(mocker):
    def etags(bucket, prefix):
        if prefix.startswith("interactive/"):
            return {"index.html": "a", "app.js": "MODIFIÉ"}
        return {"index.html": "a", "app.js": "b"}

    mocker.patch("web.publications.s3.etags_under", side_effect=etags)
    assert snapshot_drifted("d", "pub") is True
