---
name: rpe
description: Indicateurs du Réseau pour l'emploi (France Travail) — accès/présence en emploi, formation, recrutement, RSA, par territoire et par mois. Données agrégées, nationales, couvrant tout le réseau (pas seulement nos services). À distinguer d'autometa_tables_db.
---

# RPE — Tableau de bord du Réseau pour l'emploi

Données publiques du tableau de bord France Travail (`pilotage-rpe.francetravail.org`). Indicateurs officiels du **réseau pour l'emploi** : résultats d'accès à l'emploi, de formation, de recrutement et d'accompagnement, déclinés par territoire (commune → bassin → département → région) et par mois.

## En quoi c'est différent d'autometa_tables_db (à lire avant de choisir)

| | `rpe` (ce skill) | `autometa_tables_db` |
|---|---|---|
| Périmètre | **Tout le réseau pour l'emploi** (France Travail, national) | **Nos services** (les_emplois, dora, data·inclusion…) |
| Granularité | **Agrégée** (cubes par territoire/mois ; pas de niveau individuel) | **Fine / niveau enregistrement** |
| Source | Tableau de bord public France Travail | Nos bases applicatives |

En une phrase : **RPE = la vision agrégée et nationale de France Travail sur tout le réseau ; autometa_tables = nos propres données de services, granulaires.** Les mesures RPE sont des agrégats (souvent des taux) : on ne peut pas les filtrer sur nos usagers/structures, ni les ré-agréger localement (pas de numérateur/dénominateur).

## Quand demander à l'utilisateur de préciser

Si la demande peut relever des **deux** (ex. « taux d'accès à l'emploi par territoire », « données emploi par département »), **poser la question avant de requêter**, en exposant la conséquence du choix :

- **RPE** si on veut le résultat **officiel France Travail sur tout le réseau** (national/territorial, agrégé) — mais impossible de cibler nos usagers/structures, ni de descendre au niveau individuel.
- **autometa_tables_db** si on veut **nos données de services** (périmètre inclusion, granulaire) — mais ce n'est pas la vision réseau/nationale.

## Ce que contient le dataset

Datasets « métier » (les principaux) :

- **Accès et présence en emploi** — taux d'accès / de présence en emploi des demandeurs (1/3/6/12 mois, par public).
- **Description des publics** — caractéristiques des inscrits (âge, sexe, niveau de formation, BRSA, QPV, BOE…).
- **Entrants en formation** / **Sortants de formation** — entrées en formation et devenir en emploi à la sortie.
- **Taux de recours** (+ par filière) — recours des établissements au réseau (offres, recrutements).
- **Délai et taux de pourvoi des offres** (+ par filière) — taux et délai de pourvoi des offres d'emploi.
- **Satisfaction DE** / **NPS** — satisfaction des demandeurs sur l'accompagnement.
- **Fiches action** — fiches action des comités territoriaux (CTPE).
- **Focus RSA (accompagnement rénové des BRSA)** — parcours des bénéficiaires du RSA, territoires pilotes.

Dimensions transverses : géographie (commune/bassin/département/région), temps (mois), et caractéristiques publics (sexe, âge, niveau de formation, BRSA/QPV/BOE, type de parcours…). Catalogue exact dans `matometa.rpe_dataset` / `rpe_dimension` / `rpe_measure`.

## Deux chemins : en cache vs à la demande

**En cache (instantané)** — rafraîchi chaque nuit par le cron `refresh-rpe` dans le schéma `matometa`. Contient le catalogue et des **marginales** (`rpe_fact`) : chaque mesure ventilée par **une** dimension.

Schéma (`matometa`) :

- `rpe_dataset(cube_key, name, cube_id, role_id)` — `name` = nom du dataset.
- `rpe_dimension(dataset, dim_id, name, category, caption_dim, n_members)`.
- `rpe_measure(dataset, measure_id, label)` — `measure_id` = id **exact** à passer à `query()`.
- `rpe_fact(id, dataset, measure, measure_id, period, dimension, member_code, member_label, value)`.

**Toujours interroger la couverture réelle du cache** (la liste évolue avec la config du mirror — ne pas s'en remettre à une doc figée) :

```sql
SELECT dataset, dimension, count(*) AS lignes, count(DISTINCT period) AS periodes,
       min(period) AS du, max(period) AS au
FROM matometa.rpe_fact GROUP BY 1, 2 ORDER BY 1, 2;
```

Granularités géo matérialisées (selon `lib.rpe.MIRROR_GEO`, libellé canonique stocké dans `dimension`) : `dimension='Région'` (codes INSEE région, ex. `11`), `dimension='Département'` (ex. `59`), `dimension='CLPE'` (territoire, codes ex. `CLPE74001`). Référence commune↔CLPE↔INSEE : `knowledge/stats/clpe.md` (table `public.ref_clpe_ft`) — ⚠️ format de code CLPE différent côté RPE (`CLPE74001`) vs ref (`CLPE_001`), jointure non triviale. Si la granularité/période voulue n'est **pas** dans la couverture ci-dessus → requête à la demande.

⚠️ Les **libellés de mesure ne sont pas uniques** (plusieurs mesures sources partagent un même `measure`, ex. mensuel vs cumul 12 mois). **Toujours filtrer/désambiguïser par `measure_id`**, pas par `measure`. Pour trouver le bon id : `SELECT measure_id, label FROM matometa.rpe_measure WHERE dataset=:ds AND label ILIKE :q`.

```python
from sqlalchemy import text
from web.db import get_db

with get_db() as s:
    rows = s.execute(text("""
        SELECT member_label AS region, period, value, measure_id
        FROM matometa.rpe_fact
        WHERE dataset = :ds AND dimension = 'Région' AND measure_id = :mid
        ORDER BY value DESC
    """), {"ds": "Accès et présence en emploi",
           "mid": "Accès à l'emploi - Accès à l'emploi à 6 mois (switch cumul 12 mois) %"}).all()
```

**À la demande (`lib.rpe`)** — pour ce qui n'est pas en cache : un **croisement multi-dimensions** (région × sexe × âge), une **autre période**, un **grain fin** (bassin, commune), une mesure absente du cache.

```python
from lib.rpe import RpeClient

c = RpeClient.connect()                          # login httpx, sans navigateur
c.datasets(); c.measures(ds); c.dimensions(ds)   # explorer le catalogue
rows = c.query(
    "Accès et présence en emploi",
    dimensions=[{"dim": "C_TERRITOIRE_ID", "hPos": 0, "lPos": 1}, "C_LBLSEXE"],  # région × sexe
    measures=["Accès à l'emploi - Accès à l'emploi à 6 mois (switch cumul 12 mois) %"],
)
c.close()
```

`measures` : passer le `measure_id` exact, **ou** son libellé / une variante (la résolution est tolérante à la casse, aux apostrophes droites/courbes et aux espaces — match normalisé sur id et label ; un log `mesure résolue X → Y` confirme). Si aucune correspondance unique → valeurs de présence (1.0) + avertissement. Niveau géographique via `lPos` sur `C_TERRITOIRE_ID` (1 = région, 0 = département ; grains fins : explorer).

⚠️ **Filtrage géographique : filtrer côté client, pas côté serveur.** Le `filters=` serveur ignore le niveau hiérarchique (hardcodé level 0) → un `filters={"C_TERRITOIRE_ID": ["11"]}` renvoie des **valeurs fausses** (il matche un territoire feuille codé 11, pas la région). Méthode fiable : **ventiler par la dimension géo** (`C_TERRITOIRE_ID:1`) **et filtrer les lignes du résultat** par `member_code`/`Région_code`. En CLI, utiliser `--where`.

**Croisement multi-dimensions + filtre géo, en un seul appel CLI** (le cas « IDF par sexe × âge ») :

```bash
python skills/rpe/scripts/query.py --query "Accès et présence en emploi" \
  --dim C_TERRITOIRE_ID:1 --dim C_LBLSEXE --dim C_LBLCATEGORIEAGE \
  --measure "Accès à l'emploi - Accès à l'emploi à 6 mois (switch cumul 12 mois) %" \
  --where "Région_code=11"
```
→ 8 lignes (2 sexes × 4 tranches d'âge) pour l'Île-de-France.

**Série temporelle (évolution sur les mois)** — utiliser `--month <dim date>` (la dimension de catégorie « 2. Date », ex. `D_DATEFPRIO`, `D_DATETAETPED`). ⚠️ Indispensable : `--month` ventile par mois **et lève le filtre de période** du template (sinon la requête est figée sur le dernier mois → une seule ligne). Trouver la mesure et la dim date avec `--measures DS --grep …` et `--dims DS --grep date` :

```bash
python skills/rpe/scripts/query.py --query "Entrants en formation" \
  --dim C_TERRITOIRE_ID:1 --month D_DATEFPRIO \
  --measure "Région - Entrants en formation" --where "Région_code=53"
```
→ une ligne par mois pour la Bretagne (code région 53).

**Mesures « (switch) » — mensuel vs cumul.** Certaines mesures dont l'id contient `(switch)` basculent entre mensuel et cumul 12 mois selon une variable `ddVars` (souvent `Switch`). Par défaut elles renvoient le **cumul**. Pour le **mensuel**, ajouter `--ddvar Switch=0` (inspecter les bascules d'un dataset : `python -c "from lib.rpe import RpeClient,_RES; …_RES['sel']['ddVars']"`). Exemple série mensuelle nette :

```bash
python skills/rpe/scripts/query.py --query "Entrants en formation" \
  --dim C_TERRITOIRE_ID:1 --month D_DATEFPRIO \
  --measure "Entrant en formation (switch)" --ddvar Switch=0 --where "Région_code=53"
```

⚠️ **`measure` / `measure_id` à `null` et `value` = 1.0** dans le résultat = l'id de mesure n'a pas été reconnu (repli « présence » du serveur). Reprendre l'id **exact** depuis `--measures … --grep …` / `rpe_measure`. La lib loggue un avertissement dans ce cas.

## Trouver le bon indicateur (routage)

`matometa.rpe_chart` documente chaque graphe du tableau de bord source : `chart_title`, `cube_name`, `measures_shown` (noms des mesures affichées), `dims_shown`. C'est la façon la plus rapide de router une question vers le bon cube/mesure (les graphes ne montrent que le sous-ensemble pertinent des mesures, avec un libellé lisible).

```sql
SELECT chart_title, cube_name, measures_shown, dims_shown
FROM matometa.rpe_chart
WHERE chart_title ILIKE :q OR array_to_string(measures_shown, ' ') ILIKE :q;
```

Puis interroger le cube avec la mesure trouvée — `query()` résout le nom de mesure en identifiant technique.

## Combien de temps

- En cache : instantané (SQL local).
- À la demande, cube déjà calculé côté serveur : ~30 ms.
- À la demande, **nouveau** croisement (cache serveur froid) : **1 à 20 s** au premier appel, puis ~30 ms. Pour de gros balayages, rester séquentiel ou ≤4 en parallèle (serveur public).

## Script

`skills/rpe/scripts/query.py` — explorer le catalogue et lancer une requête en CLI (`--list`, `--measures`, `--dims`, `--query`).
