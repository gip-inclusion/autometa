# DOD-19

**Critère** — [lentille gap-hunter : fuite du jeton ; précision du demandeur] Matomo suit chaque déclinaison sous une URL lisible, `/interactive/{slug}/{clé}/`, transmise au traceur à la place de l'URL réelle : la clé et le libellé sont écrits par le cron dans le fichier de données, le jeton n'y figure jamais. Le jeton ne sort pas de l'URL : ni dans l'URL suivie par Matomo, ni dans le titre de l'onglet, ni dans le nom des fichiers exportés. Révision 2026-10-02 — l'URL suivie par Matomo reste `/interactive/{slug}/{clé}/` ; les garanties « le jeton n'y figure jamais » ne concernent que les tableaux obfusqués : sans obfuscation, le jeton est la clé (DOD-4). Revalidé le 2026-10-02.
**Commande** — `uv run --frozen pytest browser/test_variants_page.py tests/test_dashboards_routes.py -k dod_19 -q`
**Code de sortie** — 0
**Sortie** — 

```
.....                                                                    [100%]
=============================== warnings summary ===============================
tests/test_dashboards_routes.py::test_dod_19_detail_warns_when_the_page_of_a_converted_dashboard_can_leak_the_token[multi-template]
  /Users/louije/Development/gip/Autometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
5 passed, 91 deselected, 1 warning in 2.18s
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
