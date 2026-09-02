> **Vérifié par** — `scripts/check_test_quality.py` et ruff (PT0xx) dans `make lint` ; `diff-cover` dans `make diff-cover`, donc dans la CI seulement. La suppression d'un test n'est vue par **personne**.

pytest uniquement : pas de `unittest` (ni `TestCase`, ni imports depuis le package `unittest`). Pour les mocks, utiliser le fixture **`mocker`** de **pytest-mock** (`mocker.patch`, `mocker.MagicMock`, etc.), pas `unittest.mock`.

`@pytest.mark.parametrize` dès qu’un même comportement est vérifié avec des entrées différentes. Ne pas dupliquer des fonctions de test pour varier les entrées.

Préférer des **fonctions usine** définies dans le fichier de test (ou localement dans le test) aux fixtures qui ne font que construire des objets sans état partagé ni setup/teardown. La duplication de données initiales explicites est acceptable ; la duplication de logique paramétrable ne l’est pas.

Si un comportement mérite un exemple, l’écrire comme test. Les tests sont la documentation vivante.

Marqueurs de test — un test non marqué doit tourner sans service ni credentials. Chaque marqueur correspond à une disposition CI :

- `@pytest.mark.integration` : a besoin d'une infra locale que la CI provisionne (Postgres, Redis). Exécuté en CI et exclu de `make test`.
- `@pytest.mark.external` : tape sur de vrais services externes / credentials (Matomo, Metabase, Notion…). **Aucune CI ne l'exécute aujourd'hui** — à lancer à la main (`pytest -m external`, credentials requis). Le workflow nightly qui les portera arrive en phase 8 de la stratégie de tests.
- `@pytest.mark.e2e` : parcours complet en process (runner + Redis + SSE, agent faké).
- `@pytest.mark.browser` : parcours de navigateur Playwright (`browser/`), contre une application servie — locale ou review app. Job CI dédié, hors `required_status_checks`. Voir `docs/paved-road/l3-e2e.md`.

> Le job E2E (`browser/`) est un workflow séparé, hors `required_status_checks` : il ne bloque
> pas tant qu'il n'a pas prouvé sa stabilité. Le couloir unit l'exclut par `not browser`.
>
> La CI de PR découpe en trois jobs : `unit` (`-m "not integration and not e2e and not external"`, sans service), `integration` (`-m "integration or e2e"`, avec Postgres+Redis), puis `coverage` (fusion + plancher). `e2e` tourne donc dans le job `integration`, pas dans le couloir unit. Le hook `pre-commit` rejoue le couloir unit hermétique (`make test`) avant tout commit ; le hook `Stop` reste sur lint + tests creux uniquement.

Chaque modification de code doit avoir un test correspondant.
