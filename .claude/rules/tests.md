pytest uniquement : pas de `unittest` (ni `TestCase`, ni imports depuis le package `unittest`). Pour les mocks, utiliser le fixture **`mocker`** de **pytest-mock** (`mocker.patch`, `mocker.MagicMock`, etc.), pas `unittest.mock`.

`@pytest.mark.parametrize` dès qu’un même comportement est vérifié avec des entrées différentes. Ne pas dupliquer des fonctions de test pour varier les entrées.

Préférer des **fonctions usine** définies dans le fichier de test (ou localement dans le test) aux fixtures qui ne font que construire des objets sans état partagé ni setup/teardown. La duplication de données initiales explicites est acceptable ; la duplication de logique paramétrable ne l’est pas.

Si un comportement mérite un exemple, l’écrire comme test. Les tests sont la documentation vivante.

Marqueurs de test — un test non marqué doit tourner sans service ni credentials. Chaque marqueur correspond à une disposition CI :

- `@pytest.mark.integration` : a besoin d'une infra locale que la CI provisionne (Postgres, Redis). Exécuté en CI et exclu de `make test`.
- `@pytest.mark.external` : tape sur de vrais services externes / credentials (Matomo, Metabase, Notion…). **Nightly uniquement**, exclu de la CI de PR et de `make test`.
- `@pytest.mark.e2e` : parcours complet en process (runner + Redis + SSE, agent faké).

> La CI de PR découpe en trois jobs : `unit` (`-m "not integration and not e2e and not external"`, sans service), `integration` (`-m "integration or e2e"`, avec Postgres+Redis), puis `coverage` (fusion + plancher). `e2e` tourne donc dans le job `integration`, pas dans le couloir unit. Le hook `pre-commit` rejoue le couloir unit hermétique (`make test`) avant tout commit ; le hook `Stop` reste sur lint + tests creux uniquement.

Chaque modification de code doit avoir un test correspondant.
