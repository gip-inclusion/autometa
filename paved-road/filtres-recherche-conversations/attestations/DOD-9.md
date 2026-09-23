# DOD-9

**Critère** — [du brief : « une recherche par mots clé avec les embeddings » ; décision « sens + repli »] Quand je tape des mots dans la barre de recherche, je retrouve les conversations dont le contenu correspond au sens de ma recherche, même si les mots exacts ne figurent pas dans le titre, les plus proches d'abord.
**Commande** — `uv run --frozen pytest tests/test_conversation_search.py -k dod_9`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/lelia/Documents/PDI/Matometa
configfile: pytest.ini
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0, playwright-0.9.0, base-url-2.1.0
collected 4 items / 3 deselected / 1 selected

tests/test_conversation_search.py .                                      [100%]

=============================== warnings summary ===============================
tests/test_conversation_search.py::test_dod_9_la_recherche_retrouve_par_le_sens
  /home/lelia/Documents/PDI/Matometa/tests/conftest.py:133: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 1 passed, 3 deselected, 1 warning in 5.79s ==================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `6cd58b74c91788ffa7261b163e9668c58a8c6cc7` |
| `lib` | `a580a088ff4c75f87a9e28870302eb565ff9aa95` |
| `scripts` | `a45951726895543020a4c2a42a465100e54867af` |
| `skills` | `dd8aa7e4657f23ca6318affdd7d03b904dc21766` |
| `alembic` | `f16ee5bae3fe5b0639825bd366dde9877bb77884` |
| `tests` | `5edd7586f3a0e5ec149869e86dbe0af5245b6adf` |
| `browser` | `67359247a91488e0eb2275b40232d88e41cdbb0f` |

**Verdict** — démontré.
