# DOD-20

**Critère** — [précision du demandeur : la liste ou le mapping ne doit pas être dans le code du TDB] Publier ou rafraîchir la publication d'un tableau multi-sources est refusé, avec la raison affichée sur la page d'édition, si un jeton déclaré apparaît dans le contenu d'un fichier du tableau (page, script, fichier de données ou autre). Le seul emplacement admis d'un jeton est le nom du fichier `data/{jeton}.json`. Une liste de clés ou de libellés dans le code n'est pas refusée : seul le jeton ouvre l'accès. Révision 2026-10-02 — le refus ne s'applique qu'aux tableaux obfusqués : sans obfuscation, la clé est publique par construction (DOD-4). Revalidé le 2026-10-02.
**Commande** — `uv run --frozen pytest tests/test_variants_lib.py tests/test_publications.py tests/test_cron.py tests/test_dashboards_routes.py -k dod_20 -q`
**Code de sortie** — 0
**Sortie** — 

```
........                                                                 [100%]
=============================== warnings summary ===============================
tests/test_publications.py::test_dod_20_publish_is_refused_when_a_file_carries_a_token
  /Users/louije/Development/gip/Autometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
8 passed, 238 deselected, 1 warning in 1.25s
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `198be3e0ca19c7344346b460f47632a7997c1a8b` |
| `lib` | `84a1e7d287295a59e01cb7c7538590bc2859cd10` |
| `scripts` | `1db5541ee291f83cc7f58352cd6e10d88881ebf6` |
| `skills` | `7b027d42d1f92f23e8e4d4564a145642ca751e07` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `ec3304b8db8c97656f9df8252c87a26ab455a11c` |
| `browser` | `3838fcc50ff5c25b4f975d5d2bdbc060a2ca9cca` |

**Verdict** — démontré.
