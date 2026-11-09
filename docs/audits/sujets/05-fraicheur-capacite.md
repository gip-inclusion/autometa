# Sujet 5 — Fraîcheur des données et capacité du lot du matin

Statut : **solution choisie** (07/10) · Constats : F26, F28, F13 · Suivi :
`../2026-10-07-dashboards-suivi.md`

## Le problème, en clair

### Problème 1 — Des TDB en panne que personne ne suit (F26)

Chaque jour, une vingtaine de TDB échouent à se mettre à jour, et quinze échouent tous les jours
depuis au moins deux semaines. Une seule alerte Slack part, au premier échec, puis plus rien.
L'auteur du TDB n'est jamais prévenu.

### Problème 2 — Le lot du matin approche de sa limite (F28, F13)

Les scripts des TDB internes tournent l'un après l'autre. Depuis #236, le lot a une heure maximum ;
au-delà, les TDB restants sont sautés ce jour-là. Mesuré : 54 minutes le 05/10, contre 42 à 49
minutes les jours précédents, soit environ 10 % de marge. Le lot tourne dans un conteneur de
512 Mo, déjà tué plusieurs fois faute de mémoire en septembre.

Mesures sur 7 jours : 103 TDB, 47 minutes au total en série, 11 secondes en médiane. Les plus
longs : `tdb-gestionnaires-territoires` (environ 5 min), puis quatre TDB d'environ 2 min 30.

## Décisions (07/10)

### Une alerte récapitulative quotidienne pour les devs

Chaque matin, après le lot, **un seul message Slack** liste tous les TDB en échec, avec pour
chacun depuis quand il échoue et le type d'erreur. Il est destiné aux devs, pour qu'ils voient et
traitent ces échecs.

### Le lot en parallèle, prudemment

Une seule file d'attente, avec plusieurs « guichets » : dès qu'un guichet se libère, il prend le
TDB suivant. Personne ne range les TDB dans des groupes. Des groupes fixes dans le planificateur
ne seraient de toute façon pas possibles : `cron.json` est limité à 5 lignes par Scalingo, et
elles sont toutes utilisées.

Pour ne pas surcharger les sources de données (Metabase, autometa_tables, data·inclusion, Matomo),
utilisées en même temps par l'équipe dès 8 h :

- **2 guichets au départ**, pas 4. On surveille une ou deux semaines les erreurs et les temps de
  réponse des sources, puis on monte à 3 ou 4 si tout va bien ;
- **les TDB lourds passent seuls**, dans un couloir à part, un par un. Est « lourd » un TDB qui a
  pris plus d'une minute la veille. Le tri est automatique, à partir des durées mesurées ;
- un **conteneur plus grand** (L au lieu de M), pour la mémoire de plusieurs scripts à la fois ;
- un TDB qui plante ne bloque pas les autres guichets.

Effet attendu : le lot passe d'environ 47 minutes à environ 25 minutes avec 2 guichets, et tient
la croissance du nombre de TDB.

**Écarté pour l'instant** : une limite du nombre de requêtes simultanées par source, à placer dans
la façade. C'est plus précis, mais aussi plus de travail. À reconsidérer une fois la façade
généralisée (sujet 4).

## Points de cohérence

- **Sujet 2.** Les publications ont déjà une alerte quotidienne. Le récapitulatif peut les
  inclure, pour n'avoir qu'un seul message.
- **Zone critique.** La taille du conteneur se règle dans `cron.json`, désormais classé zone
  critique : relecture humaine.

## Implémentation lot C (19/10)

### Mesures avant de coder (base de production, lecture seule)

Lot `tableaux-internes`, du 12/10 au 19/10 :

| Jour | Durée réelle | TDB | En échec | Somme des TDB lourds* | Estimation à 2 guichets, 1 lourd à la fois |
|---|---|---|---|---|---|
| 12/10 | 42 min | 106 | 8 | 20 min | 21 min |
| 13/10 | 46 min | 104 | 8 | 26 min | 26 min |
| 14/10 | 55 min | 93 | 4 | 38 min | 38 min |
| 15/10 | 50 min | 91 | 4 | 34 min | 34 min |
| 16/10 | 51 min | 93 | 4 | 35 min | 35 min |
| 17/10 | 48 min | 94 | 3 | 33 min | 33 min |
| 18/10 | 48 min | 94 | 5 | 27 min | 27 min |
| 19/10 | 52 min | 101 | 3 | 32 min | 32 min |

\* TDB qui avaient pris plus d'une minute au passage précédent.

- **Les archivages n'ont pas raccourci le lot.** Il est passé de 104 à 93 TDB, mais il dure
  48 à 55 minutes depuis le 14/10 (contre 42 à 46 avant) : 8 à 20 % de marge. Le 14/10, il restait
  5 minutes.
- **Les TDB lourds font les deux tiers du temps.** Le 19/10, 13 TDB de plus d'une minute ont pris
  35 minutes sur 52. Médiane d'un TDB : 8 secondes. Les plus longs sur 7 jours :
  `fin-parcours-adoption` (8 min en moyenne, jusqu'à 10), puis `statistiques-structures`,
  `tdb-gestionnaires-territoires` et `ab-test-recherche-dora` (3 à 5 min).
- **Les échecs ont fondu** : 3 à 5 TDB par jour depuis le 14/10, contre 8 à 10 avant, et aucune
  publication en échec depuis le 15/10. `dashboard-okr` échoue tous les jours.

### Ce qui est fait

- **Guichets.** `web/cron.py` exécute le lot avec N guichets (`--workers N`, 1 par défaut, donc
  inchangé pour les autres lots). Les TDB lourds passent dans deux couloirs au plus, donc jamais
  plus de deux à la fois ; les autres guichets prennent les TDB légers dès qu'ils sont libres, et
  les couloirs lourds les aident une fois leurs TDB passés. À 2 guichets, les deux sont des
  couloirs lourds. Les plus longs partent en premier. Est lourd un TDB qui a pris plus d'une minute
  à son dernier passage ; un nouveau TDB est léger. Le budget d'une heure reste vérifié avant
  chaque départ, et un TDB qui plante ne bloque aucun guichet.
- **Récapitulatif Slack.** À la fin du lot `tableaux-internes`, un seul message dans le canal
  d'alerte : nombre de TDB, durée du lot, part du budget consommée, nombre de guichets, puis chaque
  TDB en échec, le plus ancien d'abord, avec la date de son premier échec depuis son dernier succès
  et le type d'erreur (nom de la dernière exception de la sortie, ou « timeout »). Le message part
  aussi quand rien n'échoue, pour suivre la marge chaque jour pendant la période d'observation.
- **`cron.json`** (zone critique) : `--workers 2` et conteneur **L** pour `tableaux-internes`.
- Tests : jamais plus de deux TDB lourds à la fois, un guichet léger libre pendant ce temps, plus longs d'abord, aucune tâche perdue quand une tâche lève
  (1 et 3 guichets), contenu du récapitulatif, type d'erreur, ancienneté de l'échec (intégration).

### Décisions et pourquoi

- **Deux TDB lourds à la fois (Q1, décidé le 19/10).** Avec un seul TDB lourd à la fois, le lot
  ne pouvait pas descendre sous la somme des TDB lourds (20 à 38 min selon le jour, soit ~35 min
  attendues). Avec deux, le lot devrait tomber vers 26 à 30 min (moitié du travail total, et pas
  moins que `fin-parcours-adoption`, 8 à 10 min) : estimation, à confirmer par le récapitulatif.
  Le prix : jusqu'à deux requêtes lourdes simultanées sur Metabase et les bases, au lieu d'une.
  Plus de deux exigerait d'abord une limite de débit commune aux API (voir « Reste à faire »).
- **Couloir lourd et guichets légers plutôt qu'un verrou.** Avec un simple verrou sur les TDB
  lourds, un guichet qui tombe sur un deuxième TDB lourd attend sans rien faire.
- **Durée lue au dernier passage**, quel qu'il soit, plutôt qu'une moyenne : une seule requête, celle
  que la page `/cron` fait déjà.
- **Nombre de guichets en argument dans `cron.json`** plutôt qu'en variable d'environnement : chaque
  montée (3, puis 4) passe par une relecture.
- **Alertes au premier échec conservées (Q2).** Le récapitulatif s'y ajoute. Les retirer est
  réversible et se décidera après observation.
- **Récapitulatif envoyé même sans échec (Q3)**, le temps de l'observation.
- **Marge sur `/cron` et alerte sous 25 % reportées à C10 (Q4).** Le récapitulatif donne déjà la
  marge chaque matin ; DOD-5 et DOD-6 seront traités avec la fraîcheur de la donnée.
- **Pool de connexions inchangé** (2 + 3 de débordement) : chaque guichet n'en tient qu'une à la
  fois, et brièvement. À revoir au-delà de 4 guichets.

### Reste à faire

- Mesurer une à deux semaines : durée du lot (dans le récapitulatif), erreurs et temps de réponse
  de Metabase, Matomo et des bases avec deux TDB lourds à la fois, mémoire du conteneur L. Puis
  décider de 3 ou 4 guichets.
- Limite de débit commune aux API (Matomo, Metabase, bases), à traiter dans un sujet à part :
  chaque TDB tourne dans son propre processus, une limite en mémoire ne serait pas partagée. Elle
  devrait aussi couvrir les conversations de l'agent, qui interrogent les mêmes API. Préalable à
  toute concurrence au-delà de deux TDB lourds.
- Regarder `fin-parcours-adoption` (8 à 10 min) : c'est le plus gros gain unitaire, et désormais
  la borne basse du lot.
- Afficher la marge sur `/cron` et alerter sous 25 % (DOD-5 et DOD-6 de C10) : reporté à C10.
- Fraîcheur de la donnée et alerte à l'auteur (DOD-1 à DOD-4 de C10) : hors lot C.
