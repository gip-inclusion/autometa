# Build — écrire le code et ses tests

But : réaliser les critères du contrat, dans les conventions du dépôt, sans intervention humaine.

Le demandeur ne voit rien pendant cette étape. S'il relance `/paved-road:paved-road`, donne-lui
l'état en français.

## Dans l'ordre

**1. Relire les règles** qui s'appliquent aux fichiers que tu vas toucher (`.claude/rules/`).
Elles sont chargées automatiquement pour la plupart ; certaines ne le sont qu'à la lecture d'un
fichier correspondant. En cas de doute, ouvre-les.

**2. TDD, par tranche verticale.** Un critère à la fois : test rouge, code, test vert. Ce n'est
pas une consigne de style, c'est une règle vérifiée — `advance` refuse un vert dont le rouge n'a
pas été journalisé, et refuse aussi un vert joué sur la même empreinte de code que son rouge.

L'ordre, pour chaque critère :

1. écris le test — rien à committer ;
2. journalise le rouge :
   `make paved-road-advance DOD=DOD-3 RED=1 CMD='uv run --frozen pytest tests/test_x.py -k dod_3'`.
   La commande doit sortir en code non nul, sinon `advance` refuse ;
3. écris le code, puis committe le test et le code ensemble ;
4. joue le vert, à l'étape `prove` : même commande, sans `RED=1`. Lui exige un arbre propre.

Pendant les cycles, lance **le fichier de tests concerné** (`pytest tests/test_x.py -q`, ≈ 5 s),
jamais la suite complète. Le hook `pre-commit` rejoue la suite hermétique au moment du commit, une
fois par tranche : c'est le bon moment, ne le double pas.

**3. Nommer les tests qui prouvent.** Le test qui démontrera `DOD-3` porte `dod_3` dans son
identifiant : `test_dod_3_le_fichier_porte_le_titre_du_rapport`, et la commande le **sélectionne**
par `-k dod_3` ou par `…::test_dod_3_…`. Le mot `dod_3` posé ailleurs sur la ligne ne compte pas.
Sans ça, `prove` refuse la preuve — un `test_health` qui passe ne démontre pas un critère.

**4. Ne pas toucher à ce qui te vérifie.** Ni les seuils (`gates.toml`, `pyproject.toml`), ni les
workflows, ni les scripts `check_*`, ni les tests existants pour les faire taire. Affaiblir une
assertion d'un test que ton diff touche, ou ajouter un `skip` sans `# Why:` : `check_test_quality.py`
le refuse. **Supprimer** un test, en revanche, n'est vu par aucun contrôle — il ne compare que les
tests présents des deux côtés. C'est une règle que personne ne vérifie à ta place.

Si un garde-fou te bloque légitimement, corrige le code. S'il te bloque à tort, c'est une
friction : écris-la dans le journal du parcours, et dis-le. Ne la contourne pas.

**5. Quand tu penses avoir fini** : passe à `review.md`. C'est `review.md` qui lancera `advance`
vers `prove`, pas toi — la relecture vient avant les preuves, et elle peut te renvoyer coder.

## Ce qui te reprend en cours de route

Ces contrôles tournent tout seuls. Ils ne sont pas des obstacles, ils t'évitent de découvrir le
problème trois heures plus tard :

| Quand | Quoi |
|---|---|
| à chaque écriture | `check_python.py` (docstrings, commentaires, SQL, `except`) et ruff sur le fichier |
| à `make lint` | les mêmes conventions sur tout le dépôt, avec leur dette gelée dans `gates.toml` |
| à la fin d'un tour | lint et détecteurs de tests creux — tu ne peux pas conclure sur du rouge |
| au commit | la suite unitaire hermétique, sans service, ≈ 20 s |
| en intégration continue | lint Python, lint front (Biome), sécurité, unitaires, intégration, couverture, migrations, image |

La CI ne lit **aucun** artefact du parcours : ni le contrat, ni le journal, ni les attestations.
Personne ne rejouera tes preuves ailleurs. C'est ici qu'elles se tiennent, ou nulle part.

## Une contrainte du dépôt à connaître

Les tableaux de bord de production vivent **hors du dépôt** et importent `lib/dashboard_api.py`.
Retirer une fonction de cette façade, ou changer sa signature, casse des tableaux de bord vivants
qu'aucun diff ne montre. L'élargir est sans risque ; la réduire, non.
