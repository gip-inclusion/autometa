# DOD-5

**Critère** — [du brief : « de manière sécurisée »] Si quelqu'un a modifié un article dans Zendesk entre ma lecture de la proposition et mon approbation, cet article est laissé tel quel, il m'est nommé, et les autres sont modifiés normalement.
**Commande** — `uv run --frozen pytest tests/test_zendesk_changeset.py -k dod_5_`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/louije/Development/gip/Autometa/.worktrees/zendesk-write
configfile: pytest.ini
plugins: mock-3.15.1, cov-7.1.0, playwright-0.9.0, base-url-2.1.0, anyio-4.13.0
collected 29 items / 27 deselected / 2 selected

tests/test_zendesk_changeset.py ..                                       [100%]

======================= 2 passed, 27 deselected in 0.21s =======================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `8eb2cf007275989e4a2a4bfe7c94dbfaa0bb8dba` |
| `lib` | `e4c37a630af5ec7efd518afc71219e0b979f9df0` |
| `scripts` | `a4d9138781a04d96661f9e8647f4867cf513d756` |
| `skills` | `5ec2ad1357a5812863cabcdb9882e380f736d0ac` |
| `alembic` | `78d86fc32fd67e7792b9050474ff4a65a14753d5` |
| `tests` | `a415a4099bd1cc9093741d1229f6a38cf66a13e0` |
| `browser` | `a74249cb83790092cc89b32a05588fe41bf6fc70` |

**Verdict** — démontré.
