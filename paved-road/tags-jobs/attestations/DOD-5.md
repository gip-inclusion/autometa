# DOD-5

**Critère** — La liste se trie par activité récente (date du dernier run, défaut actuel inchangé), par nom, ou par tag (les pipelines regroupés par leur premier tag, les non tagués à la fin). Une valeur de tri inconnue retombe sur le défaut.
**Commande** — `uv run --frozen pytest -m 'integration or not integration' tests/test_job_tags.py -k dod_5`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-tags-jobs
configfile: pytest.ini
plugins: mock-3.15.1, anyio-4.14.2, base-url-2.1.0, xdist-3.8.0, cov-7.1.0, playwright-0.9.0
collected 33 items / 26 deselected / 7 selected

tests/test_job_tags.py .......                                           [100%]

=============================== warnings summary ===============================
tests/test_job_tags.py::test_dod_5_sort_orders_the_list[activite-expected0]
  /home/alexisakinyemi/autometa-tags-jobs/tests/conftest.py:134: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 7 passed, 26 deselected, 1 warning in 4.23s ==================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `7cfe7f53a088eb3b0c6a14a81cfb3b07ad8b9445` |
| `lib` | `df7dc062d0dfe6a1d31a7c781a81dadd24497e38` |
| `scripts` | `292a403984c75249c2c2f0fdf5ab4fea8e0fbf98` |
| `skills` | `2d7fd7e69581ce896f16d3c9e05fddddd1b8b110` |
| `alembic` | `d9e074f002cadfb42bf5139d4c62d8fb609ad29b` |
| `tests` | `65a526b2e425f065dc41b031e332372032491eb6` |
| `browser` | `dfe75ce4dc33000439b7557f008534f53280bc8b` |

**Verdict** — démontré.
