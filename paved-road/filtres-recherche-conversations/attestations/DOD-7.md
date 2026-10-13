# DOD-7

**Critère** — [cas limite : combinaison sans résultat] Quand mes filtres ne renvoient aucune conversation, je vois un message clair indiquant qu'aucun résultat ne correspond, et je peux effacer les filtres pour revenir à la liste complète.
**Commande** — `uv run --frozen pytest tests/test_conversations_filters.py -k dod_7`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/lelia/Documents/PDI/Matometa
configfile: pytest.ini
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0, playwright-0.9.0, base-url-2.1.0
collected 5 items / 4 deselected / 1 selected

tests/test_conversations_filters.py .                                    [100%]

=============================== warnings summary ===============================
tests/test_conversations_filters.py::test_dod_7_message_et_effacement_quand_les_filtres_ne_donnent_rien
  /home/lelia/Documents/PDI/Matometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 1 passed, 4 deselected, 1 warning in 10.15s ==================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `612fdda32d4dcf8f0cd87b297ca1f955091b39d0` |
| `lib` | `a580a088ff4c75f87a9e28870302eb565ff9aa95` |
| `scripts` | `a45951726895543020a4c2a42a465100e54867af` |
| `skills` | `dd8aa7e4657f23ca6318affdd7d03b904dc21766` |
| `alembic` | `f16ee5bae3fe5b0639825bd366dde9877bb77884` |
| `tests` | `03707af0df6129119c77136aa9f70fb4ce3d9f40` |
| `browser` | `67359247a91488e0eb2275b40232d88e41cdbb0f` |

**Verdict** — démontré.
