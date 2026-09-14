# Rétro — tableaux de bord multi-sources

Parcours joué le 2026-09-14, dans une session ordinaire (pas `make claude`) et dans un worktree,
en suivant les fichiers du plugin à la main. Vingt critères, tous démontrés ; deux passes de la
lentille `design-coherence`, trois bloqueurs corrigés ; une passe de smoke pilotée par Playwright
faute d'outils MCP de navigateur dans la session.

## Ce qui a frotté

- **Le worktree n'a pas d'outillage prêt.** `git commit` échoue tant que `.venv/bin` n'est pas sur le
  `PATH` (le hook appelle `pre-commit` nu), et `make setup` y crée une seconde pile Docker, avec des
  volumes vides, dont le bucket ne porte pas le nom que `.env` attend : les envois S3 échouaient en
  silence jusqu'à la passe de smoke, qui l'a révélé. Un `make doctor` qui vérifie l'existence du
  bucket éviterait la surprise.
- **`advance` refuse `-p no:cacheprovider`**, mais rien ne le dit avant d'essayer ; la liste des
  commandes admises mérite d'être imprimée dans le refus.
- **`tests/test_lint_baseline.py` fait tomber la suite hermétique** pour un docstring de deux lignes
  dans un fichier de test neuf, avec un message qui ne nomme pas la règle : il a fallu relancer
  `scripts/check_lint_baseline.py` à la main pour comprendre.
- **Cycle d'import.** Élargir la façade (`lib.dashboard_api`) vers un module qui lit la base a créé
  deux cycles (`lib.dashboards` → `web.cron` → façade). Réparés en faisant importer `lib.facade_imports`
  plutôt que la façade dans le code applicatif, et en sortant `DashboardNotFound` dans un module feuille.
  Ce sont les seuls fichiers du diff hors périmètre fonctionnel.
- **Le contrat portait une tension** (DOD-2 « jeton inconnu → lien invalide » contre DOD-14 « jeton sans
  fichier → message distinct ») que ni le gap-hunter ni moi n'avons vue à l'écriture : sans liste des
  jetons dans la copie publiée, la page ne peut pas distinguer les deux. La lentille l'a trouvée ;
  résolue par un message combiné, documenté dans le test et dans le guide.

## Ce qui a surpris

- Le conteneur Matomo Tag Manager envoie sa page vue **avant** `mtm.Start`, et le plugin Heatmap
  envoie l'URL réelle dans sa requête de configuration. Il a fallu une sonde dans un vrai navigateur
  (trois essais) pour trouver la combinaison qui ne laisse jamais partir le jeton : charger le
  conteneur après `setCustomUrl` et désactiver Heatmap Session Recording.
- Les tests de navigateur peuvent semer leurs données par la bibliothèque de l'application, mais le
  watcher pousse le dossier sur S3 en deux secondes, et l'application le restaure au boot : le
  nettoyage doit aussi vider S3, sinon les tableaux de test reviennent.

## Coût

Session unique, de l'assessment à la preuve : environ 2,2 M de tokens d'entrée cumulés (dont trois
sous-agents de lecture à 150 k, 100 k et 100 k), une quarantaine de commits et relances de la suite
hermétique à trois minutes chacune. Le poste le plus cher a été la suite complète rejouée par le hook
à chaque commit — sept fois — pour des changements dont un seul fichier de tests avait bougé.
