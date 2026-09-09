---
name: smoke
description: Passe de smoke exploratoire du paved road (L4) — parcourir l'application dans un vrai navigateur via MCP, avant d'ouvrir la PR, pour voir ce qu'aucun test n'avait prévu. À utiliser quand une PR touche une interface (template, fichier statique, route) et que le code est dans son dernier état.
---

# Smoke — regarder, pas garantir

Le pendant exploratoire des tests E2E. L'E2E vérifie ce qui était prévu et rend un verdict ; le smoke
attrape **ce que personne n'avait pensé à tester** — le bouton présent mais illisible, la page qui rame,
le fichier téléchargé techniquement conforme et visuellement raté.

Ce n'est pas un guardrail. Il ne bloque rien, il ne se rejoue pas à l'identique, et son adaptabilité est
exactement ce que la rigidité d'un test ne sait pas faire. Le produit de la passe est **des captures et un
compte rendu en français**, destinés à la personne qui a demandé la fonctionnalité.

## Les deux bornes

**Une seule passe par PR**, sur le dernier état du code avant ouverture — pas à chaque correction. Un
parcours d'une dizaine d'étapes coûte plusieurs centaines de milliers de tokens d'entrée, l'essentiel
venant des captures. `plan` refuse une seconde passe sur le même état de l'interface ; une correction qui
touche réellement l'interface change l'empreinte et rouvre une passe.

**Uniquement si la PR touche une interface** — un template, un fichier statique, une route. Ailleurs, un
parcours de navigateur ne révèle rien que les autres niveaux ne voient déjà. `plan` le tranche seul.

## Ce qui ne doit jamais atteindre le dépôt

Le dépôt est **public** et le produit manipule des données sur des demandeurs d'emploi.

- **Aucune capture dans l'arbre de travail.** Elles vivent sous `~/.cache/autometa/smoke/`, hors du dépôt,
  et transitent par les artefacts de CI ou un commentaire de PR. `verify` refuse de fermer une passe qui
  laisse un binaire derrière elle.
- **Aucune donnée réelle dans une capture.** La base locale porte de vraies conversations et de vrais
  rapports. Créer les données du parcours pendant la passe, ou choisir un contenu manifestement fictif.
  Si une donnée réelle apparaît malgré tout à l'écran, la capture reste locale et n'est pas publiée : le
  dire dans le rapport.

`gitleaks` ne protège pas de ça — il cherche des motifs de secrets, pas des noms de personnes, et n'ouvre
pas une image.

## Dérouler la passe

**1. Ouvrir la passe.**

```bash
uv run --frozen python scripts/smoke.py plan --base main
```

Sortie 0 sans répertoire : rien à smoker, s'arrêter là. Sinon la commande donne le répertoire de sortie et
le parcours, dérivé des `DOD-N` du `definition-of-done.md`. Ajouter `--dod <chemin>` si la Definition of
Done ne porte pas le nom de la branche.

**2. Lancer l'application** sur son dernier état : `make dev` (elle sert sur `http://127.0.0.1:5000`).
Sur une review app, viser son URL — le second mode d'entrée du niveau E2E s'applique aussi ici.

**3. Jouer le parcours au navigateur**, via les outils MCP `mcp__claude-in-chrome__*` (charger d'abord
leurs schémas avec un seul `ToolSearch`). Un `DOD-N` par étape, dans l'ordre, une capture par étape,
nommée `<numéro>-<ce-qu-on-voit>.png` dans le répertoire de sortie.

Suivre le parcours prévu, mais **regarder au-delà de lui** — c'est la seule raison d'être de ce niveau :

- ce qui est illisible, tronqué, mal aligné, ou invisible sans scroller
- ce qui est lent — attendre vraiment, et noter combien de temps
- ce qui arrive quand on s'écarte : recharger en plein milieu, revenir en arrière, ouvrir dans un autre
  ordre, redimensionner en fenêtre étroite
- ce que le fichier produit donne une fois ouvert, pas seulement une fois téléchargé
- les erreurs de la console et les requêtes en échec (`read_console_messages`, `read_network_requests`)

Ne jamais déclencher d'`alert()`/`confirm()` : un dialogue modal fige la session MCP.

**4. Écrire le compte rendu** dans `rapport.md`, au même endroit que les captures. En français, pour la
personne qui a demandé la fonctionnalité — pas pour un relecteur de code. Une section « Le parcours »
(chaque `DOD-N`, ce qui s'est passé, la capture correspondante) et une section « Ce que je n'avais pas
prévu » qui est le vrai produit de la passe. Écrire aussi ce qui est allé bien : un rapport qui ne
contient que des reproches ne dit pas si la fonctionnalité tient debout.

**5. Fermer la passe.**

```bash
uv run --frozen python scripts/smoke.py verify --dir <répertoire donné par plan>
```

Elle échoue tant qu'un binaire traîne dans l'arbre de travail, ou tant que `rapport.md` est absent.

**6. Rattacher au parcours.** Ce que la passe a trouvé se corrige avant d'ouvrir la PR, ou remonte dans
la description de PR comme réserve assumée. Le rapport et les captures s'attachent à la PR par un
commentaire — jamais par un commit.
