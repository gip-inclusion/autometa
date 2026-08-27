# L3 — E2E

L'evidence cesse d'être une capture produite par l'agent et devient un test exécutable, rejouable
par la CI, par un humain et par n'importe quel agent.

Les parcours vivent dans `browser/`, portent le marqueur `browser`, et tournent contre une
application servie — jamais en processus. `make e2e` les rejoue en local ; le workflow `E2E` les
rejoue sur chaque PR et chaque nuit.

## Un test par critère

Un critère `DOD-N` démontré par navigateur donne un test nommé `test_dod_<n>`, dans un module dédié
à la fonctionnalité. La correspondance est mécanique : elle se lit dans le nom, et l'attestation de
L2 cite la commande qui l'exécute.

**Au plus cinq critères par fonctionnalité sont démontrés par navigateur.**
`scripts/check_test_quality.py` refuse le sixième. Sans cette borne, le coût récurrent de L3 suit la
verbosité de la demande. Au-delà, la preuve retombe sur une forme déterministe moins coûteuse — un
test unitaire, une assertion sur l'artefact produit — ou sur le smoke de L4.

## Ce qu'un parcours de navigateur ne démontre pas

Playwright pilote un navigateur. Il ne lit pas l'intérieur d'un PDF, et une mesure de volumétrie est
instable sur un runner partagé. Un critère portant sur le contenu d'un fichier se démontre par une
assertion sur l'artefact produit ; un critère de volumétrie par une mesure en nightly, hors du
chemin bloquant.

## Le socle

Au jour 1, aucune fonctionnalité existante ne porte de `DOD-N` : une suite qui n'aurait que des
tests `test_dod_<n>` serait vide et ne défendrait rien. `browser/test_socle.py` couvre donc cinq
parcours que toute fonctionnalité future traverse — accueil, création d'une conversation, ouverture
d'un rapport, `/selftest`, liste des tableaux de bord. C'est ce qui rend la non-régression vraie dès
la première fonctionnalité au lieu de la dixième.

Le socle s'écarte sur un point de la liste du design : `/interactive/` sert des objets déposés dans
le stockage objet, qu'un test ne peut pas créer par la surface HTTP de l'application — sa
volumétrie diffère donc entre une instance locale et une review app. Son contrat (aucune source
servie, aucune remontée de chemin) est déjà couvert par `tests/test_interactive_serving.py`. Le
socle couvre à la place `/dashboards`, la page d'où l'on y accède, qui s'affiche partout.

## Hors de `required_status_checks`

Le job `E2E` ne bloque pas la fusion tant qu'il n'a pas prouvé son absence d'instabilité — le
cliquet du design appliqué à son propre outillage. Il vit dans son propre workflow, comme
`dependencies.yml` et pour la même raison : `scripts/check_required_checks.py` exige que tout job
déclaré dans `ci.yml` soit inscrit dans les checks requis.

## Accès aux review apps

> **Ce chemin existe mais n'est pas encore emprunté.** Le workflow `E2E` sert l'application dans
> le runner (`E2E_BASE_URL: http://127.0.0.1:8000`) et ne vise aucune review app. Le secret
> `REVIEW_APP_HTPASSWD` n'existe ni dans les secrets du dépôt ni dans ceux de l'organisation :
> en l'état, le second mode d'entrée décrit ci-dessous ne peut pas fonctionner. Les deux moitiés
> sont posées — le proxy sait l'accepter, la suite sait l'envoyer — le câble entre les deux est
> reporté au palier 2, en couloir nightly : c'est le bon endroit pour un test qui dépend d'un
> déploiement externe.

Toute instance déployée est derrière oauth2-proxy. Un navigateur piloté n'a pas de compte Google.

Le proxy accepte donc un **second mode d'entrée par secret technique**, connu du seul runner de CI :
`bin/with_review_app_auth.sh` écrit un fichier `htpasswd` au démarrage de l'instance, à partir de
`REVIEW_APP_HTPASSWD`, et seulement si `AUTOMETA_ENV` vaut `review`. Un visiteur humain voit
toujours l'écran de connexion ; la review app n'est à aucun moment consultable depuis internet.

Le secret porté par l'instance est un **hachage bcrypt** — le mot de passe en clair ne quitte jamais
les secrets GitHub. La suite le consomme par `E2E_HTTP_CREDENTIALS`, au format `utilisateur:motdepasse`,
et la cible par `E2E_BASE_URL`.

Dispenser certaines routes d'authentification a été écarté : ces pages resteraient publiques
pendant toute la vie de la review app.

Ce que le proxy garantit, vérifié sur oauth2-proxy v7.15.0, la version qu'installe le buildpack :

- sans identifiants, une requête reçoit l'écran de connexion, jamais l'application ;
- un mot de passe invalide ne passe pas davantage ;
- `X-Forwarded-Email` et `X-Forwarded-User` fournis par le client sont **remplacés** par le proxy,
  donc l'identité n'est pas forgeable ;
- une session ouverte par ce second mode ne porte pas d'adresse e-mail : l'application applique
  `DEFAULT_USER`. C'est l'identité sous laquelle les parcours s'exécutent sur une review app.

### Ce qui reste à valider

Le mécanisme a été validé contre le binaire réel et le script de démarrage réel, avec la
configuration oauth2-proxy de `autometa-staging`. Il n'a **pas** encore été validé sur une review
app déployée : le déploiement automatique des review apps est désactivé, aucune n'existe, et leur
pilotage par la CI est encore une PR ouverte. Tant que cette passe n'a pas eu lieu, L3 tourne en
local et en CI contre une instance lancée par le job — pas contre une review app.

Pour la lever, une fois `REVIEW_APP_HTPASSWD` posé sur `autometa-staging` (les review apps en
héritent) et une review app déployée :

```
curl -sS -o /dev/null -w '%{http_code}\n' https://<review-app>/           # attendu : 403
curl -sS -o /dev/null -w '%{http_code}\n' -u "$CREDENTIALS" https://<review-app>/   # attendu : 200
E2E_BASE_URL=https://<review-app> E2E_HTTP_CREDENTIALS="$CREDENTIALS" make e2e
```
