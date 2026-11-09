# Rétro — viz-quality-paved

Parcours mené en une session, par un agent à qui le demandeur avait délégué son rôle, pour être
comparé à la PR #228, écrite sur la même demande mais code d'abord.

**Ce que le contrat d'abord a changé.** Lire la surface avant d'écrire (R1) a fixé la forme de
`DOD-7` : les scripts `create_dashboard` / `update_dashboard` tournent *avant* que l'agent écrive le
HTML, la vérification ne peut donc pas y vivre — c'est une consigne d'enchaînement, et elle ne se
prouve pas. La lentille `gap-hunter` a apporté six critères que le brief ne contenait pas et qui
étaient tous des faux échecs ou des blocages en production : le tag manager Matomo, les données en
direct, le bloc `#error` rempli sans rien écrire en console (convention `showError`), le premier
usage sans `index.html`, l'attente sans fin, l'acharnement sans borne. Elle a raté le navigateur
absent de l'image de production, trouvé à la lecture du `Dockerfile` (`DOD-14`).

**Ce que la lentille `design-coherence` a attrapé.** Deux vrais défauts que tous les tests
laissaient passer : un Chart.js ou un Plot vide dessine ses axes et passait pour tracé (le test
utilisait un canvas brut, sans bibliothèque) ; et `DOD-9` promettait qu'un tableau de bord live
pouvait réussir hors de l'application, ce qui était faux par ricochet. Le second était une erreur
de contrat, pas de code : la révision datée l'a rendue visible au lieu de la maquiller. La passe 2
a trouvé une régression du correctif (légende de couleur Plot), confirmée par un vrai rendu de Plot
avant d'être corrigée. Trois passes pour converger.

**Frictions.**

- **Le hook `pre-commit` est inutilisable dans un worktree git.** Git exporte pour ses hooks un
  `GIT_INDEX_FILE` absolu quand le dépôt est un worktree ; `tests/test_lint_baseline.py` lance
  `git -C <tmp> add`, qui écrit alors dans l'index *réel* (`force.py`, `parti.py`, `suivi.py`), et
  pre-commit refuse (« files were modified by this hook »). Aucun commit touchant un `.py` ne passe
  depuis un worktree, alors que `paved-road-start` est pensé pour eux. Contournement, sans
  `--no-verify` : committer dans un clone ordinaire où les hooks tournent en entier, puis déplacer la
  branche du worktree sur ce commit. Le clone doit vivre hors de `/tmp` : sinon
  `tests/test_hook_settings.py` échoue, la garde d'écriture autorisant `/tmp`. Correctif suggéré,
  hors de ce parcours : que les tests qui lancent `git` retirent les `GIT_*` de l'environnement.
- **Un rouge qui est une erreur de collecte est accepté.** Les douze rouges sont sortis en 2 — le
  module n'existait pas encore. C'est le cas honnête du premier cycle TDD, mais le contrôle ne
  distingue pas « le test échoue » de « le test ne se charge pas ».
- **L'environnement bloque `build → prove` pour des preuves qui n'en dépendent pas.** `doctor` exige
  Docker, Postgres, Redis, MinIO et un `.env` ; ce poste partagé n'a rien de tout ça démarré pour ce
  dépôt, et `make setup` aurait pris les ports 5432 / 9000 / 6379 (le dernier déjà occupé). Les
  attestations, elles, s'écrivent sans égard à l'état : les douze critères démontrables le sont,
  mais le parcours reste en `build`.
- **« Seul `advance` écrit au journal »** contredit « écris la friction dans le journal du parcours »
  (SKILL.md). Les frictions sont donc ici.
- **La borne « au plus cinq critères par un test de bout en bout »** est ambiguë pour des tests de
  navigateur qui ne passent pas par l'application : six critères ont un test Chromium, servis
  localement, rapides et hors réseau.

**Limites assumées, à reprendre si l'usage les montre** : D3 écrit à la main jugé sur ses formes
(axes compris) ; Chart.js aux données objets orientées y ; `Plot.ruleY([0])` masque un Plot vide ;
une boucle JavaScript infinie après chargement n'est pas bornée.

**Différences avec la PR #228** (même intention, code d'abord) : #228 prend aussi une URL servie
en cible et produit une capture d'écran, rétrograde polices et images en avertissement, et juge les
libellés Chart.js ; ce parcours n'a rien de tout cela, faute de phrase du brief à laquelle le
rattacher. Il a en plus : le verdict « délai dépassé », le bloc `#error` et « Chargement… », la borne
de trois tentatives, le dédoublonnage des valeurs cassées, le jugement des marques Plot et de sa
légende, et une promesse honnête sur les données en direct. Environ 165 lignes de bibliothèque
contre 202.

**Coût.** Une session ; `/cost` non disponible depuis la session incubée.
