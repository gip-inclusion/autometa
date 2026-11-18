# DOD-1

**Critère** — Quand j'écris `@nom-du-job` dans un message, alors l'agent reçoit, en plus de mon message, la consigne du job, ses derniers runs (statut, date) et un extrait de la dernière sortie réussie.
**Commande** — `uv run --frozen pytest tests/test_job_mentions.py tests/test_conversations_api.py tests/test_jobs_lib.py tests/test_jobs_routes.py -k dod_1_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/appsahl/matometa-pr276
configfile: pytest.ini
plugins: mock-3.15.1, anyio-4.14.2, base-url-2.1.0, xdist-3.8.0, cov-7.1.0, playwright-0.9.0
collected 114 items / 103 deselected / 11 selected

tests/test_job_mentions.py ..........                                    [ 90%]
tests/test_conversations_api.py .                                        [100%]

=============================== warnings summary ===============================
tests/test_conversations_api.py::test_dod_1_send_message_injects_job_mention_context
  /home/alexisakinyemi/appsahl/matometa-pr276/tests/conftest.py:134: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 11 passed, 103 deselected, 1 warning in 2.97s =================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `1324c874e05b7e97905045911db2da8621361dc3` |
| `lib` | `363fb83c04fd49eda278dfaae15a240794db6a65` |
| `scripts` | `fede7ed92dc545bad1d364bda2d39ea9f5ca8bc6` |
| `skills` | `d9b3f7e8d79f38fd66cd4f704d2268e52812ee89` |
| `alembic` | `721a99ff6297ddd1dee4c4ee28055c3f27ef05f7` |
| `tests` | `81eae863bff6d32fafaa57c757a8c9e5741ed08a` |
| `browser` | `c581b2841ec949edfd394d6518c056dc11c5a954` |

**Verdict** — démontré.
