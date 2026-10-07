# DOD-4

**Critère** — [du brief : « mapping between facet and uuid is stored in our work db »] Les déclinaisons d'un tableau de bord (clé, libellé, jeton) sont enregistrées en base. Le jeton est généré par l'outil, jamais choisi à la main, et reste le même d'un rafraîchissement à l'autre : un lien partagé continue de fonctionner après le passage du cron et après une republication. Révision 2026-10-02 — par défaut, le jeton d'une déclinaison est sa clé (`?q=78`, `data/78.json`) ; il est un UUID généré par l'outil seulement quand le tableau le demande (`update_dashboard --obfuscate-variants`), et alors pour toutes ses déclinaisons. Changer ce mode sur un tableau qui a déjà des déclinaisons est refusé : les liens partagés casseraient. Le jeton reste stable dans les deux modes. Motif : un nom de fichier lisible suffit tant que le lien n'a pas à être secret. Revalidé le 2026-10-02. Révision 2026-10-07 — quiconque peut modifier le tableau peut activer ou désactiver l'obfuscation à tout moment, déclinaisons déjà déclarées comprises (`update_dashboard --obfuscate-variants true|false`). Chaque déclinaison reçoit alors le jeton du nouveau mode, et son fichier de données le suit, en interne comme dans chaque snapshot publié : aucun contenu n'est perdu et aucun cron n'est à relancer. Les liens partagés de l'ancien mode cessent de fonctionner, ce que la commande signale. Si une copie échoue, aucun jeton ne change. Motif : refuser obligeait à retirer puis redéclarer chaque déclinaison. Revalidé le 2026-10-07. La commande nomme aussi chaque publication active : son lien public garde l'ancien jeton jusqu'à son prochain rafraîchissement, sans borne si celui-ci est en pause. L'agent propose de la rafraîchir (`publish_dashboard refresh`) mais ne le fait pas d'office.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_dashboard_skill_scripts.py tests/test_publications.py -k dod_4 -q`
**Code de sortie** — 0
**Sortie** — 

```
...................                                                      [100%]
=============================== warnings summary ===============================
tests/test_publications.py::test_dod_4_refresh_reports_whether_the_public_copy_was_synced
  /Users/louije/Development/gip/autometa-multi-source/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
19 passed, 48 deselected, 1 warning in 1.63s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `24dea1b178864a4e9d2d459702281b8dd5467486` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5b7ce2570650d81cd71ce8c342b44d048849b78f` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
