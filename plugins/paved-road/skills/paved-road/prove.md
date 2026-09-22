# Prove — une preuve par critère

But : pour chaque `DOD-N`, une commande réelle, son code de sortie, et le lien entre cette preuve
et l'état exact du code qu'elle a prouvé.

Le demandeur verra le résultat dans la description de PR : démontré, non démontré, périmé.

## Dans l'ordre

Chaque critère se prouve en deux temps, et le second refuse de partir sans le premier.

**Le rouge**, une fois le test écrit, avant que le code existe. Rien n'a besoin d'être committé :

```
make paved-road-advance DOD=DOD-1 RED=1 CMD='uv run --frozen pytest tests/test_rapports.py -k dod_1'
```

La commande doit sortir en code non nul. Si elle sort en 0, `advance` refuse : un test qui passe
avant que le code existe ne démontre rien. Le rouge journalise l'empreinte du périmètre prouvé au
moment où il tourne — c'est elle qui servira à constater qu'il s'est passé quelque chose ensuite.

**Le vert**, une fois le code écrit et committé :

```
make paved-road-advance DOD=DOD-1 CMD='uv run --frozen pytest tests/test_rapports.py -k dod_1'
```

`advance` exécute la commande, écrit `paved-road/<slug>/attestations/DOD-1.md` — la commande, son
code de sortie, la sortie tronquée, les empreintes d'arbre de `web`, `lib`, `scripts`, `skills`,
`alembic`, `tests`, et le verdict.

Il refuse le vert dans deux cas : aucun rouge n'a été journalisé pour ce critère, ou le rouge et le
vert portent sur la même empreinte de périmètre — rien n'a été implémenté entre les deux, donc le
cycle n'a pas eu lieu.

Le vert exige un arbre propre sur les chemins prouvés : il inscrit une empreinte, et elle ne
décrirait pas un travail non committé. Le rouge, lui, tourne sur l'arbre de travail — c'est bien
le moment où le test existe et où le code n'existe pas encore. L'empreinte qu'il journalise est
celle du HEAD, donc du code d'avant, ce qui suffit à la distinguer de celle du vert.

## Quelle preuve pour quel critère

| Le critère parle de… | Preuve admise |
|---|---|
| un comportement du code (`web/`, `lib/`) | un test unitaire ciblé : `uv run --frozen pytest tests/… -k dod_N` |
| un parcours dans le navigateur | un `test_dod_N` sous `browser/`, joué par le workflow E2E |
| une migration | `alembic check`, plus la migration jouée sur une base fraîche |
| un chiffre : volumétrie, durée | un test qui mesure et assère un seuil, comme les autres |

**Toucher `web/templates/` ou `web/static/` engage un test de navigateur.** Le contrôle des
attestations refuse alors le parcours tant qu'aucun `browser/…::test_dod_N_…` ne porte le nom d'un
critère. `make test` est le couloir hermétique : il exclut `browser`, donc un critère qui parle de
retour arrière, d'adresse ou d'historique htmx passait « démontré » sur un test qui ne charge aucune
page. Seule la **présence** du test est vérifiée ici — une panne du moteur de conteneurs ne bloque
donc pas le parcours ; son exécution appartient à `make e2e` et au workflow E2E, joué sur chaque PR.

Quand un rebase ou un commit sous un chemin prouvé périme toutes les attestations d'un coup,
`make paved-road-reprove` les rejoue en un lot, chacune avec la commande qu'elle a inscrite. Le
rouge du cycle initial reste valable : il porte l'empreinte du code d'avant, donc différente de
l'actuelle. Une preuve que le rejeu ne fait plus passer est nommée, et le lot sort en 1.

Rien ne rejoue ces preuves ailleurs : la CI ne lit aucun artefact du parcours. Le verdict que vous
lisez est celui de la commande qui a tourné ici, sur l'empreinte de code inscrite dans
l'attestation. Une preuve périmée se voit à cette empreinte, pas à un rejeu.

Un `SKILL.md` ou un fichier de `knowledge/` n'a pas de vérificateur : aucun script ne sait dire si
son contenu fait ce qu'il annonce. Un critère qui porte dessus ne se démontre pas par ce mécanisme
— dites-le au demandeur plutôt que de ranger une preuve creuse.

## Ce qu'une commande de preuve ne peut pas être

La liste des commandes admises est fermée : `uv run --frozen pytest`, `uv run --frozen alembic`,
`uv run --frozen python <fichier>`. Tout le reste est refusé avant même d'être exécuté.

- `true`, `echo`, `make` — y compris `make test` : une cible de Makefile démontrait n'importe quel
  critère, puisque le lien commande-critère ne s'applique qu'à ce qui lance pytest ;
- `python -c`, `python -m`, `python --version`, le REPL nu : une preuve exécute un fichier
  versionné, que la relecture peut lire ;
- `pytest --collect-only`, `--co` : collecter n'est pas exécuter ;
- un `pytest` qui sort en 0 sans qu'un seul test ait tourné — un `-k` qui ne désigne rien ;
- un test sans rapport avec le critère. Le lien se fait par la **valeur d'un `-k`** ou par un
  identifiant `…::test_dod_n_…`, pas par le mot `dod_n` posé ailleurs sur la ligne :
  `pytest tests/ --junitxml=/tmp/dod-1.xml` lançait la suite entière et satisfaisait le contrôle.

Ces refus s'appliquent à l'écriture de l'attestation **et** à sa relecture, ce qui rattrape une
attestation ancienne dont la commande ne serait plus recevable.

Ce qu'ils ne font pas, et il faut le savoir : **rien ne rejoue la commande à la relecture**. Une
attestation entièrement écrite à la main, avec un code de sortie 0 et les bonnes empreintes, passe
tous les contrôles. Ces refus ferment la preuve *vide* et la preuve *hors dépôt* ; ils ne sont pas
une frontière de sécurité, et ils ne peuvent pas l'être — c'est le même agent qui écrit la preuve
et qui la relit. Ce qui tient réellement : l'empreinte périme l'attestation dès que le code change,
et le pair lit le contrat et les preuves dans la PR.

Ces règles ferment la preuve vide. Elles ne jugent pas si le corps du test démontre vraiment le
bon comportement — aucun programme ne sait le faire. C'est au pair de lire les critères, et à la
lentille d'avoir comparé le code au contrat à l'étape précédente.

## Si un critère ne peut pas être prouvé

Ne le maquille pas. Laisse-le « non démontré », et écris pourquoi dans la description de PR.
Un critère non démontré et annoncé se discute ; un critère faussement démontré se découvre en
production.

Si le critère lui-même est infaisable — le contrat s'est trompé — c'est une révision : dis-le au
demandeur, révise la ligne concernée en la datant (`Révision AAAA-MM-JJ`), et reprends.

## Quand tout est démontré

Passe à `pr.md`.

## Si une preuve devient périmée

Elle le devient dès qu'un des chemins empreintés change — y compris quand `main` avance sous toi
et que tu rebases. `make paved-road-checks CHECK=attestations` le dit, et `advance` refuse de
passer à l'état suivant : c'est une panne réparable, tu reprends les preuves concernées. Si l'interface a changé, le smoke est à refaire
aussi, et il demande une présence humaine : préviens le demandeur au lieu de le découvrir avec lui.
