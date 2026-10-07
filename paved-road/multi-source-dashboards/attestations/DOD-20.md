# DOD-20

**Critère** — [précision du demandeur : la liste ou le mapping ne doit pas être dans le code du TDB] Publier ou rafraîchir la publication d'un tableau multi-sources est refusé, avec la raison affichée sur la page d'édition, si un jeton déclaré apparaît dans le contenu d'un fichier du tableau (page, script, fichier de données ou autre). Le seul emplacement admis d'un jeton est le nom du fichier `data/{jeton}.json`. Une liste de clés ou de libellés dans le code n'est pas refusée : seul le jeton ouvre l'accès. Révision 2026-10-02 — le refus ne s'applique qu'aux tableaux obfusqués : sans obfuscation, la clé est publique par construction (DOD-4). Revalidé le 2026-10-02.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_publications.py tests/test_cron.py tests/test_dashboards_routes.py -k dod_20 -q`
**Code de sortie** — 0
**Sortie** — 

```
........                                                                 [100%]
=============================== warnings summary ===============================
tests/test_publications.py::test_dod_20_publish_is_refused_when_a_file_carries_a_token
  /Users/louije/Development/gip/autometa-multi-source/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
8 passed, 243 deselected, 1 warning in 1.36s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `025f36cf58659e483324d1a6cfc73a6df9549b0a` |
| `lib` | `857b7b5f0d013efe0b7a0a185fffe090db79d3a7` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `4cd9e2f4ac9726e2a7cfd34ece88e82aaea1f745` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `5e5459c774ff6e8e55e094e1d678b509109e3517` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
