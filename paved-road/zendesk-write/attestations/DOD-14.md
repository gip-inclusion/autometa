# DOD-14

**Critère** — Approuver une proposition déjà appliquée, ou défaire une modification jamais appliquée ou déjà défaite, n'écrit rien : Autometa me dit dans quel état elle est.
**Commande** — `uv run --frozen pytest tests/test_zendesk_changeset.py -k dod_14_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/louije/Development/gip/Autometa
configfile: pytest.ini
plugins: mock-3.15.1, cov-7.1.0, playwright-0.9.0, base-url-2.1.0, anyio-4.13.0
collected 41 items / 37 deselected / 4 selected

tests/test_zendesk_changeset.py ....                                     [100%]

======================= 4 passed, 37 deselected in 0.30s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `8eb2cf007275989e4a2a4bfe7c94dbfaa0bb8dba` |
| `lib` | `d45b63aab61ba3d3a105194be3f9b36b88839e1e` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `7c128e350e1ce205275fe35019db54ad2e264e52` |
| `alembic` | `78d86fc32fd67e7792b9050474ff4a65a14753d5` |
| `tests` | `f837990eb25439dc209d8b09d6e651e6f4d4fdb2` |
| `browser` | `a74249cb83790092cc89b32a05588fe41bf6fc70` |

**Verdict** — démontré.
