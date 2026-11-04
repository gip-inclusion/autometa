# DOD-8

**Critère** — La page `/jobs` affiche les tags de chaque pipeline dans la liste, une barre de filtres avec le nombre de pipelines par tag, le choix du tri, et l'éditeur de tags du pipeline sélectionné.
**Commande** — `uv run --frozen pytest -m 'integration or not integration' tests/test_job_tags.py -k dod_8`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-tags-jobs
configfile: pytest.ini
plugins: mock-3.15.1, anyio-4.14.2, base-url-2.1.0, xdist-3.8.0, cov-7.1.0, playwright-0.9.0
collected 33 items / 32 deselected / 1 selected

tests/test_job_tags.py .                                                 [100%]

=============================== warnings summary ===============================
tests/test_job_tags.py::test_dod_8_jobs_page_renders_filters_sort_and_editor
  /home/alexisakinyemi/autometa-tags-jobs/tests/conftest.py:134: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 1 passed, 32 deselected, 1 warning in 3.25s ==================
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
