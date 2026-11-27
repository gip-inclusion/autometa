# Alerte quotidienne : tableaux de bord sans visite depuis 60 jours

## Intention

Repérer chaque jour les TDB que personne n'ouvre plus, pour que l'équipe prévienne leurs propriétaires
et les archive en un clic. Un seul message Slack agrégé, qui s'allonge jusqu'à archivage.

## Objectifs

- Un message par jour sur `SLACK_ALERT_CHANNEL`, listant les TDB non archivés, créés il y a plus de
  60 jours, sans aucune visite Matomo sur les 60 derniers jours.
- Par TDB : titre, nom du propriétaire, lien vers la fiche (`BASE_URL/dashboards/<slug>`, bouton Archiver).
- Un TDB réapparaît chaque jour tant qu'il n'est pas archivé. Aucune liste : aucun message.

## Non-objectifs

- Pas de tag Slack des propriétaires (nom seulement, pour l'instant).
- Pas d'archivage automatique, pas de nouvelle route d'archivage.
- Pas de stockage des visites en base, pas de migration.

## Anti-objectifs

- Proposer d'archiver un TDB réellement consulté (faux positif).
- Une durée qui croît avec le nombre de TDB.

## Contraintes

- Matomo site 224 (Autometa) compte les vues dans l'app (`/interactive/<slug>`) et publiques
  (`statistiques.inclusion.gouv.fr/dashboards/<slug>`).
- Les archives Matomo semaine, mois et plage regroupent la traîne en « … - Others » : inutilisables.
  Les archives jour sont précalculées et sans regroupement observé (≤ 45 TDB par jour).

## Approches

- O1. Un appel `Actions.getPageUrls` sur `last60` : écarté, la traîne « /interactive/ - Others » produit de faux positifs.
- O2. Un appel segmenté par TDB : exact, mais N appels segmentés, durée proportionnelle au nombre de
  TDB, contraire à `.claude/rules/api.md`. Écarté.
- O3. Date de dernière visite stockée en base : migration et zone critique, même regroupement au rafraîchissement. Écarté.
- O4. **Retenu** : 60 requêtes `Actions.getPageUrls` en `period=day`, regroupées en un seul appel
  `API.getBulkRequest` (mesuré : 1,1 s pour 60 jours). Coût constant, exact, aucune boucle de requêtes
  au sens de `.claude/rules/api.md`, aucune modification de `lib/`.

## Décisions

- Vu = au moins une visite sur un chemin commençant par `/interactive/<slug>` ou `/dashboards/<slug>`.
  La fiche Autometa (`/dashboards/<slug>/edit`) ne compte pas : c'est la page où l'alerte envoie
  archiver, et l'ouvrir ferait sortir le TDB de la liste. Le chemin public `/dashboards/<slug>` compte.
- Échec Matomo (appel global, ou un jour renvoyé en `{"result": "error"}` dans la réponse groupée) :
  aucun envoi, la tâche échoue (pas de liste fausse).
- Tâche du batch `maintenance` (6 h).
- Nom du propriétaire déduit de `first_author_email` (`prenom.nom@…` → « Prenom Nom », sans accents),
  sinon l'email. (choix de l'agent)

## Laissé au builder

- Forme exacte du message, ordre de la liste (choix proposé : par titre).
