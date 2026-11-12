# DOD-1

**Critère** — Quand je coche un tag dans l'éditeur d'un pipeline, sur `/jobs/pipelines/<id>`, alors le pipeline porte ce tag : il apparaît sur le pipeline dans la liste et reste coché au rechargement.
**Commande** — `uv run --frozen pytest -m 'integration or not integration' tests/test_job_tags.py -k dod_1`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-tags-jobs
configfile: pytest.ini
plugins: mock-3.15.1, anyio-4.14.2, base-url-2.1.0, xdist-3.8.0, cov-7.1.0, playwright-0.9.0
collected 34 items / 31 deselected / 3 selected

tests/test_job_tags.py ...                                               [100%]

=============================== warnings summary ===============================
tests/test_job_tags.py::test_dod_1_toggle_adds_tag_and_page_shows_it
  /home/alexisakinyemi/autometa-tags-jobs/tests/conftest.py:134: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 3 passed, 31 deselected, 1 warning in 4.70s ==================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `b8cfb4066576a4b4c98ef148c7d72542e457a38c` |
| `lib` | `c5135807bc77a7caacf4728bd52e29a2a62910b4` |
| `scripts` | `292a403984c75249c2c2f0fdf5ab4fea8e0fbf98` |
| `skills` | `2d7fd7e69581ce896f16d3c9e05fddddd1b8b110` |
| `alembic` | `d9e074f002cadfb42bf5139d4c62d8fb609ad29b` |
| `tests` | `1c268692669f865eb4c2e4f4da146e71fadc9151` |
| `browser` | `dfe75ce4dc33000439b7557f008534f53280bc8b` |

**Verdict** — démontré.
