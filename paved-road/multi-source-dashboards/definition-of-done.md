# Tableaux de bord multi-sources (déclinaisons)

## Ce que je veux

Beaucoup de tableaux de bord ont le même écran et le même comportement, seules les données changent
(un département, une structure, un réseau). Aujourd'hui on les duplique, et ça ne tient plus. Je veux
un seul tableau de bord qui sert chaque déclinaison par son propre lien, sans menu déroulant qui
donnerait accès à toutes les autres. Et je veux que ce mode soit pris en charge par l'outillage
(création, édition, cron, publication) comme n'importe quel tableau de bord.

## Ce qui devra marcher

DOD-1 — [du brief : « visiting …/?q=1234-… will ajax load the correct file »] Quand j'ouvre
  `/interactive/{slug}/?q={jeton}` avec le jeton d'une déclinaison déclarée, le tableau de bord
  affiche les données de cette seule déclinaison : son nom en en-tête, ses chiffres.

DOD-2 — [du brief : « not having a query string will soft-404 »] Sur la version publiée, sans `?q`
  ou avec un jeton inconnu, la page affiche un message « ce lien n'est pas valide », et aucune liste
  de déclinaisons, aucun sélecteur, aucun lien vers une autre déclinaison.

DOD-3 — [du brief : « /interactive/dashboard-name page with no ?q can be intercepted to show the
  toc »] Dans l'application, connecté, `/interactive/{slug}/` sans `?q` sur un tableau
  multi-sources affiche la liste des déclinaisons avec leur lien, et un lien vers la page d'édition.
  Un tableau de bord sans déclinaison n'est pas intercepté : il s'affiche comme aujourd'hui.

DOD-4 — [du brief : « mapping between facet and uuid is stored in our work db »] Les déclinaisons
  d'un tableau de bord (clé, libellé, jeton) sont enregistrées en base. Le jeton est généré par
  l'outil, jamais choisi à la main, et reste le même d'un rafraîchissement à l'autre : un lien
  partagé continue de fonctionner après le passage du cron et après une republication.

DOD-5 — [du brief : « links to every db, and json with mapping is accessible on the
  dashboard/xxxxxx/edit page »] La page d'édition liste chaque déclinaison avec son libellé, son
  lien interne, son lien public quand une publication est active, et propose un lien vers le JSON
  du mapping (clé, libellé, jeton, liens).

DOD-6 — [du brief : « single cron.py for everything … same formulas / etc. with varying params »]
  Un seul cron produit un fichier de données par déclinaison déclarée, avec les mêmes calculs pour
  chacune, et rien d'autre : pas de fichier qui liste les déclinaisons. Une déclinaison non
  déclarée n'a pas de fichier, même si la source de données la connaît.

DOD-7 — [décision 1 : déclaration explicite] Je déclare une déclinaison par le skill
  `update_dashboard` avec sa clé et son libellé, et je la retire de la même façon. Déclarer une clé
  déjà présente est refusé sans créer de doublon, même quand deux déclarations partent en même
  temps. Retirer une déclinaison supprime son fichier de données interne ; si une publication est
  active, le retrait annonce que le lien public reste en ligne jusqu'au prochain rafraîchissement.

DOD-8 — [décision 4 : basculer un TDB existant] Un tableau de bord déjà enregistré devient
  multi-sources dès qu'une déclinaison lui est déclarée : la page d'édition et l'interception de
  `/interactive/{slug}/` fonctionnent sans le recréer ni changer son slug.

DOD-9 — [du brief : « first class citizen » ; « edit the skill »] Le skill `create_dashboard`
  propose un gabarit multi-sources (page qui lit `?q`, cron qui produit un fichier par déclinaison),
  et ses instructions demandent à l'agent de proposer ce mode quand une demande vise plusieurs
  territoires ou entités sur un même écran, et d'obtenir un accord explicite avant de l'utiliser.
  Ce critère porte sur des instructions en prose : il se vérifie à la lecture, pas par un test.

DOD-10 — [condition de sûreté du lien] La copie publiée d'un tableau multi-sources ne contient
  aucun fichier qui énumère les déclinaisons ou leurs jetons, et le tableau ne transmet pas le
  jeton aux sites externes qu'il lie (pas de referrer sortant).

DOD-11 — [état initial] Un tableau multi-sources sans aucune déclinaison déclarée l'indique sur la
  page d'édition (« Aucune déclinaison »), et son cron ne produit aucun fichier de données.

DOD-12 — [lentille gap-hunter : entrée hors limites] La clé d'une déclinaison est faite de lettres
  minuscules, chiffres et tirets (1 à 64 caractères) et le libellé est obligatoire. Une clé vide,
  avec espaces ou caractères spéciaux, ou un libellé vide, est refusée en nommant le champ fautif,
  sans rien créer. Deux déclinaisons peuvent porter le même libellé : la clé reste l'identifiant, et
  elle s'affiche à côté du libellé sur la page d'édition et sur l'index interne.

DOD-13 — [lentille gap-hunter : valeur hors limites] La page valide la forme du jeton avant toute
  requête : un `?q` vide, qui n'a pas la forme d'un UUID, ou qui contient `/` ou `..`, affiche
  « ce lien n'est pas valide » sans qu'aucune requête ne parte.

DOD-14 — [lentille gap-hunter : état absent] Jeton valide mais fichier de données absent : la page
  affiche « les données de cette déclinaison ne sont pas encore disponibles », message distinct du
  lien invalide, et la page d'édition marque la déclinaison « sans données ».

DOD-15 — [lentille gap-hunter : échec partiel] Quand le calcul d'une déclinaison échoue pendant le
  cron du gabarit, les autres sont produites quand même, le fichier précédent de celle qui a
  échoué est conservé, et le cron se termine en échec en nommant les clés fautives dans son
  historique.

DOD-16 — [lentille gap-hunter : publication] Une déclinaison déclarée après une publication
  apparaît dans la copie publique au rafraîchissement suivant de cette publication, sans
  republier ; son lien public est affiché sur la page d'édition dès qu'une publication est active.

DOD-17 — [lentille gap-hunter : archivage] Archiver un tableau multi-sources ne supprime aucune
  déclinaison : jetons et libellés sont conservés, et désarchiver rétablit les mêmes liens.

DOD-18 — [lentille gap-hunter : volume] Au-delà de 20 déclinaisons, la page d'édition affiche le
  compte (« 107 déclinaisons ») et un champ de filtre sur la clé et le libellé, en gardant la liste
  complète dans la page pour permettre un copier-coller de tous les liens.

DOD-19 — [lentille gap-hunter : fuite du jeton ; précision du demandeur] Matomo suit chaque
  déclinaison sous une URL lisible, `/interactive/{slug}/{clé}/`, transmise au traceur à la place
  de l'URL réelle : la clé et le libellé sont écrits par le cron dans le fichier de données, le
  jeton n'y figure jamais. Le jeton ne sort pas de l'URL : ni dans l'URL suivie par Matomo, ni
  dans le titre de l'onglet, ni dans le nom des fichiers exportés.

DOD-20 — [précision du demandeur : la liste ou le mapping ne doit pas être dans le code du TDB]
  Publier ou rafraîchir la publication d'un tableau multi-sources est refusé, avec la raison
  affichée sur la page d'édition, si un jeton déclaré apparaît dans le contenu d'un fichier du
  tableau (page, script, fichier de données ou autre). Le seul emplacement admis d'un jeton est le
  nom du fichier `data/{jeton}.json`. Une liste de clés ou de libellés dans le code n'est pas
  refusée : seul le jeton ouvre l'accès.

## Sources lues

- `web/app.py:serve_interactive`, `web/publications.py`, `web/s3.py` — **R1** : le serveur ignore
  la chaîne de requête et la publication copie le dossier entier sans filtre. Le soft-404 (`DOD-2`)
  est donc forcément côté page ; l'absence de fichier de liste (`DOD-6`, `DOD-10`) est la seule
  protection réelle du lien.
- `web/cron.py:execute_task`, `upload_s3_results` — **R1** : le cron ne reçoit aucun paramètre et
  l'envoi vers S3 ne supprime jamais un fichier. `DOD-7` (suppression au retrait) demande un geste
  explicite ; le cron doit apprendre pour quel tableau il tourne (`DOD-6`).
- `web/routes/dashboards.py`, `web/templates/dashboard_detail.html`, `web/stores/dashboards.py` —
  **R1** : la page d'édition ne porte qu'un lien vers `/interactive/{slug}/` ; `DOD-5` s'y ajoute.
- `lib/dashboard_api.py`, `lib/facade_imports.py` — **R4** : façade versionnée, élargie seulement.
- `lib/dashboards.py`, `skills/create_dashboard`, `skills/update_dashboard` — **R1** : le scaffold
  copie le gabarit à plat (pas de sous-dossier), les skills n'ont pas de notion de déclinaison.
- `web/routes/dashboards.py:facet_filters`, `lib/taxonomy.py` — **R1** : « facette » désigne déjà
  les facettes de tags. D'où « déclinaison » à l'écran et `variant` dans le code (décision 5).
- Tableau de bord modèle `tdb-gestionnaires-territoires` (prod, S3) — **R1** : un cron national
  puis un fichier par département (107 fichiers), un menu déroulant et un fichier
  `departments.json` qui énumère tout. C'est le demi-état que `DOD-2`, `DOD-6` et `DOD-10` corrigent.
  Son `cron_timeout` est à 1 800 s en base (ligne `dashboards`), ce qui montre qu'un cron national
  tient dans l'outillage actuel — **R2**.
- Archive locale de `data/interactive/` (161 dossiers) — **R2** : 16 dossiers `*-gt` dont les
  `cron.py` (~900 lignes) diffèrent de 24 lignes (`diff` entre `bas-rhin-gt` et `doubs-gt`,
  `haut-rhin-gt`, `haute-loire-gt`, `val-de-marne-gt`) : code département, nom du territoire,
  libellés. C'est la duplication que la demande vise.
- `dashboard-rdvi-departements/app.js` (archive locale) — **R1** : précédent du `?dept=` avec
  message « aucune donnée » quand le paramètre manque ; un seul `data.json` pour tous les
  départements, donc énumérable.
- `docs/interactive-dashboards.md` — **R5** : « le cron ne voit que son propre dossier » et
  « régénérer les mêmes données dans deux dashboards est acceptable » : la duplication est la
  réponse actuelle, cette demande la remplace.
- `docs/plans/` — **R5** : aucune décision passée sur les déclinaisons ou les liens par jeton.

Aucune source de données métier consultée : la demande spécifie une fonctionnalité d'Autometa.

## Questions ouvertes

Aucune. Le listage de répertoire côté hébergement public a été vérifié le 2026-09-14 :
`https://statistiques.inclusion.gouv.fr/dashboards/` et son équivalent staging répondent par la
page « introuvable » du site, pas par une liste. Les fichiers d'une déclinaison ne sont donc
atteignables que par leur nom.

## Validation

Validé par Louis-Jean Teitelbaum (LJ) le 2026-09-14.

Cinq décisions soumises : déclaration explicite des déclinaisons, index interne avec lien vers la page d'édition, pas de révocation de lien, bascule d'un TDB existant par l'outillage sans conversion du TDB modèle, « déclinaison » à l'écran et « variant » dans le code. Deux précisions du demandeur après lecture : suivi Matomo par clé lisible (DOD-19) et refus de publication si un jeton figure dans le code (DOD-20).
