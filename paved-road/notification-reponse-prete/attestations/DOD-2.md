# DOD-2

**Critère** — [du brief : « un son associé »] Au même moment, un son court est joué pour signaler que la réponse est prête.
**Commande** — `uv run --frozen pytest tests/test_notification_sound.py -k dod_2`
**Code de sortie** — 0
**Sortie** — 

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/lelia/Documents/PDI/Matometa
configfile: pytest.ini
plugins: mock-3.15.1, cov-7.1.0, anyio-4.13.0, playwright-0.9.0, base-url-2.1.0
collected 1 item

tests/test_notification_sound.py .                                       [100%]

============================== 1 passed in 0.32s ===============================
```

**Contenu prouvé**

| Chemin | Empreinte d'arbre |
|---|---|
| `web` | `17230933983e3fc15287700e8241eb76dde90095` |
| `lib` | `8ef92f8a6e97d307ea993428c7d2da51e4c31d0e` |
| `scripts` | `eb7f648e9e474c76605a86d356b4cb994aae6050` |
| `skills` | `2c267e47b5c84d597572b03b0931082be83d92d1` |
| `alembic` | `1365c85567f3f65bccc9757e470018e7af4fbe87` |
| `tests` | `218cc246c7caa7d00753f7193133d336f45fe532` |
| `browser` | `78f1c20d1dfaa64094025b44a12c4a4825786304` |

**Verdict** — démontré.
