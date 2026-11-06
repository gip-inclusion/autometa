# DOD-3

**Critère** — Quand je mentionne un nom qui ne correspond à aucun job, ou que le service de jobs ne répond pas, alors mon message part quand même, tel que je l'ai écrit, sans erreur.
**Commande** — `uv run --frozen pytest tests/test_job_mentions.py tests/test_conversations_api.py tests/test_jobs_lib.py tests/test_jobs_routes.py -k dod_3_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/alexisakinyemi/autometa-mentions-jobs
configfile: pytest.ini
plugins: mock-3.15.1, anyio-4.14.2, base-url-2.1.0, xdist-3.8.0, cov-7.1.0, playwright-0.9.0
collected 112 items / 105 deselected / 7 selected

tests/test_job_mentions.py ......                                        [ 85%]
tests/test_conversations_api.py .                                        [100%]

=============================== warnings summary ===============================
tests/test_conversations_api.py::test_dod_3_send_message_with_unknown_mention_goes_as_written
  /home/alexisakinyemi/autometa-mentions-jobs/tests/conftest.py:134: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 7 passed, 105 deselected, 1 warning in 3.18s =================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `995e73048bf3eb625df6ec2db7ccd378861b1967` |
| `lib` | `6b3bacc885811bcf7f74b5bbb4306941d4e316fa` |
| `scripts` | `292a403984c75249c2c2f0fdf5ab4fea8e0fbf98` |
| `skills` | `51890ed4c1a6cb45d8d83e5642e499750db6ba77` |
| `alembic` | `4199ab20c8200527287a4d1328e495721ee59ab2` |
| `tests` | `39408188a9efd37eabd06bb47765bade452f80a1` |
| `browser` | `855a10abd34ac7a137c7a375515e3e60c24d8930` |

**Verdict** — démontré.
