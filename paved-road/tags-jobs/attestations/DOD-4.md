# DOD-4

**Critère** — `/jobs?tag=agent` ne liste que les pipelines tagués « agent ». Avec plusieurs tags, un pipeline doit les porter tous. Un tag que personne ne porte donne une liste vide, avec un message qui le dit. Le filtre actif reste appliqué quand j'ouvre un pipeline de la liste.
**Commande** — `uv run --frozen pytest -m 'integration or not integration' tests/test_job_tags.py -k dod_4`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-tags-jobs
configfile: pytest.ini
plugins: mock-3.15.1, anyio-4.14.2, base-url-2.1.0, xdist-3.8.0, cov-7.1.0, playwright-0.9.0
collected 34 items / 26 deselected / 8 selected

tests/test_job_tags.py ........                                          [100%]

=============================== warnings summary ===============================
tests/test_job_tags.py::test_dod_4_filter_keeps_pipelines_carrying_every_tag[?tag=agent-expected0]
  /home/alexisakinyemi/autometa-tags-jobs/tests/conftest.py:134: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 8 passed, 26 deselected, 1 warning in 5.38s ==================
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
