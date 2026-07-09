# Orchestration : dans quel ordre, et pourquoi

Comment on déploie la stratégie ([`02-strategie.md`](02-strategie.md)) dans le temps. Le détail concret de chaque phase est dans [`04-phases.md`](04-phases.md).

## Le principe organisateur : le cliquet

Chaque phase fait **une seule chose** : convertir un espoir en loi, **et** poser un **cliquet** — un plancher qui, une fois posé, ne peut plus que monter. On ne redescend jamais.

Deux types de cliquet :
- **cliquet de plancher** : une mesure chiffrée (couverture, score de mutation) qu'on ne laisse jamais redescendre ;
- **cliquet de périmètre** : un domaine où la garantie devient impossible à violer (un module typé strict, une frontière validée), et dont la surface ne peut que s'étendre.

Lien avec la dette (cf. [`01-pourquoi.md`](01-pourquoi.md)) : les premières phases ne *remboursent* pas la dette, elles la **gèlent** (elle ne peut plus grossir ni empirer). Les dernières la **remboursent**, et chaque remboursement est verrouillé.

## On ordonne par dépendance, pas par envie

Important : la liste des phases est ordonnée par **rapport rendement/effort**, mais l'ordre *réalisable* est dicté par les **dépendances techniques**. La plupart des phases sont indépendantes ; très peu ont un vrai prérequis.

### Les seules contraintes d'ordre réelles

1. **Mesurer la couverture avant de la bloquer.** La CI la mesure déjà → le plancher est débloqué immédiatement.
2. **La couverture du code modifié s'appuie sur la même mesure** → elle vient avec ou juste après le plancher.
3. **Mesurer la force des tests (mutation) suppose une suite déjà verte et stable** → légitimement vers la fin.
4. **Les hooks lancent des commandes qui doivent exister** (lint, suite) → elles existent déjà ; le détecteur de slop doit exister avant que le hook de lint ne l'impose.

### Ce qui est indépendant ou parallélisable

- **Hygiène des marqueurs + config** : trivial, n'importe quand.
- **La fondation contrats (vérificateur de types sur la façade)** : **track parallèle dès le jour 1** — ne dépend de rien du travail sur les tests. Peut démarrer en même temps que le plancher.
- **Le rangement en miroir** : l'étape **la plus repoussable**. Rien avant lui n'en a besoin (la couverture mesure le code source, pas l'emplacement des fichiers de test), et rien après lui n'en dépend strictement. C'est du confort de maintenance, pas un verrou.

## Les deux couplages à ne pas rater

C'est là que la chronologie *mord* — les seuls pièges d'ordre réels :

1. **Rendre l'unit hermétique = découper la CI en deux jobs** (un sans base de données, un avec). Chaque job ne mesure alors qu'une **partie** de la couverture. Si on a posé un plancher sur la suite entière (un seul chiffre) puis qu'on découpe, le plancher se met à ne mesurer qu'un bout → il casse ou devient faux. **Donc : quand on découpe les jobs, on fusionne la couverture des deux avant d'appliquer le plancher, dans la même PR.** Le plancher et l'hermétisation se parlent par là.

2. **Choisir « couverture de branches » ou « de lignes » *avant* de geler la baseline.** La couverture de branches est plus stricte → chiffre plus bas. Geler sur les lignes puis passer aux branches plus tard ferait chuter le chiffre et casserait le plancher. → on choisit **branches** dès le départ, on baseline une seule fois.

## La carte d'orchestration

```
Jour 1, en parallèle :
  ── A. plancher de couverture (branches) ─► couverture du code modifié ─► garde anti-tests-creux
  └─ B. fondation contrats (types sur la façade) ─► élargir au cliquet
                                                    (track totalement indépendant)

Quand les contrôles existent :
  ── C. hooks (rapprocher A et le lint du moment où on écrit)

Couplé, à faire ensemble :
  ── D. unit hermétique + découpe CI  ⟺  fusion de couverture
        (sinon le plancher de A casse — couplage n°1)

Repoussable, quand le volume gêne :
  ── E. rangement en miroir + fakes propres + factories

En dernier (suppose une suite verte) :
  ── F. mutation, évals, validation des données
```

Correspondance avec les phases numérotées de [`04-phases.md`](04-phases.md) : A = phases 1–2, C = phase 4, D = phase 5, B = phase 6, E = phase 7, F = phase 8. (Les numéros suivent un ordre de lecture, pas un ordre d'exécution strict — la carte ci-dessus prime pour décider quoi faire quand.)

## La gouvernance du cliquet

Le seul invariant à tenir dans la durée :

> **Un plancher se relève uniquement dans la PR qui l'améliore, jamais à la baisse.**

Couverture globale, seuil de couverture du diff, périmètre typé strict, score de mutation — tous suivent la même mécanique : monotones, relevés par le progrès, jamais abaissés « pour faire passer ». **Une PR qui veut baisser un plancher est, par construction, un signal de revue humaine** — elle ne doit pas passer en silence.

## La propriété qui rend tout ça tenable

On peut **s'arrêter après n'importe quelle phase** en étant strictement plus sûr qu'avant. Phases A+C (geler + fail fast) suffisent déjà à empêcher la dette de grossir ; tout le reste est du remboursement, à la cadence qu'on choisit. Il n'y a pas de big-bang à réussir d'un coup, et aucune phase ne bloque tout le repo le temps de sa mise en place.
