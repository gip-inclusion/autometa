# Build — écrire le code et ses tests

But : réaliser les critères du contrat, dans les conventions du dépôt, sans intervention humaine.

Le demandeur ne voit rien pendant cette étape. S'il relance `/paved-road:paved-road`, donne-lui
l'état en français.

## Dans l'ordre

**1. Relire les règles** qui s'appliquent aux fichiers que tu vas toucher (`.claude/rules/`).
Elles sont chargées automatiquement pour la plupart ; certaines ne le sont qu'à la lecture d'un
fichier correspondant. En cas de doute, ouvre-les.

**2. TDD, par tranche verticale.** Un critère à la fois : test rouge, code, test vert. Lance
**le fichier de tests concerné** (`pytest tests/test_x.py -q`, ≈ 5 s), jamais la suite complète à
chaque cycle. Le hook `pre-commit` rejoue la suite hermétique au moment du commit, une fois par
tranche : c'est le bon moment, ne le double pas.

**3. Nommer les tests qui prouvent.** Le test qui démontrera `DOD-3` porte `dod_3` dans son
identifiant : `test_dod_3_le_fichier_porte_le_titre_du_rapport`. Sans ça, `prove` refusera la
preuve — un `test_health` qui passe ne démontre pas un critère.

**4. Ne pas toucher à ce qui te vérifie.** Ni les seuils (`gates.toml`, `pyproject.toml`), ni les
workflows, ni les scripts `check_*`, ni les tests existants pour les faire taire. Supprimer un
test, le passer en `skip`, affaiblir une assertion : `check_test_quality.py` le refuse, et un
`skip` sans `# Why:` aussi.

Si un garde-fou te bloque légitimement, corrige le code. S'il te bloque à tort, c'est une
friction : écris-la dans le journal du parcours, et dis-le. Ne la contourne pas.

**5. Quand tu penses avoir fini** : passe à `review.md`. C'est `review.md` qui lancera `advance`
vers `prove`, pas toi — la relecture vient avant les preuves, et elle peut te renvoyer coder.

## Ce qui te reprend en cours de route

Ces contrôles tournent tout seuls. Ils ne sont pas des obstacles, ils t'évitent de découvrir le
problème trois heures plus tard :

| Quand | Quoi |
|---|---|
| à chaque écriture | `check_python.py` (six règles que ruff ne sait pas dire) et ruff sur le fichier |
| à la fin d'un tour | lint et détecteurs de tests creux — tu ne peux pas conclure sur du rouge |
| au commit | la suite unitaire hermétique, sans service, ≈ 20 s |
| en intégration continue | lint, sécurité, unitaires, intégration, couverture, migrations, image |

## Une contrainte du dépôt à connaître

Les tableaux de bord de production vivent **hors du dépôt** et importent `lib/dashboard_api.py`.
Retirer une fonction de cette façade, ou changer sa signature, casse des tableaux de bord vivants
qu'aucun diff ne montre. L'élargir est sans risque ; la réduire, non.
