# Glossaire bizdev — Framework AARRI

Référentiel commun PDI (Produits De l'Inclusion). Source : *Framework AARRI - Référentiel commun PDI* (@Hugo Simon).
Objectif : une définition par concept, partagée par toutes les équipes, pour mesurer le déploiement et l'adoption des produits et requêter les bonnes tables selon le produit.

## Règle de contexte (désambiguïsation)

- **Sans produit mentionné** → définition **générale** (couche 1, agnostique du produit).
- **Produit dans le contexte** → définition **opérationnelle du produit** (couche 2) ; à défaut, la générale.
- Produits mappés en couche 2 : **RDV-Insertion, Dora, Mon Récap, Les Emplois, Le Marché**.

## Principes

- **Unité de compte unique : l'acte métier.** Tout le funnel se mesure en actes métiers, jamais en connexions/visites.
- **2 couches** : (1) conceptuelle = le funnel AARRI et ses 5 étapes, une définition unique par concept ; (2) opérationnelle = comment chaque étape se mesure dans les données de chaque produit.
- **2 niveaux** : le funnel tourne à la fois au niveau **institutionnel** (CD, GT, SIAE, structure) et **individuel** (agent, accompagnateur).
- **Synonymes non interchangeables** — 3 étapes séquentielles distinctes :
  - Acquisition = feu vert institutionnel
  - Déploiement / Activation = embarquement
  - Adoption = rétention
- **3 cas de figure** selon l'outil : org + agents convaincus ; agent seul convaincu sans validation de son org ; org décide seule et l'agent embarque par la force des choses.
- **3 archétypes produit** (expliquent les cases vides du mapping) : SaaS institutionnel (RDV-I, Dora — funnel 2 niveaux complet), transactionnel/physique (Mon Récap — surtout Acquisition→Impact), marketplace (Les Emplois, Le Marché).

## Les 5 étapes du funnel AARRI

| Étape | Question | Mesure |
|---|---|---|
| Acquisition | L'acteur décide-t-il d'utiliser le produit ? | Feu vert / convention / compte créé |
| Activation | A-t-il franchi l'embarquement et réalisé son 1er acte métier ? | 1er acte métier |
| Rétention | Reste-t-il actif et intensifie-t-il son usage ? | Actes métiers récurrents |
| Référence | Recommande-t-il le produit à ses pairs ? | Prescription / parrainage |
| Impact | Combien d'actes métiers génère-t-il ? | Volume d'actes métiers |

### Acquisition

**Général** — Un acteur (org ou individu) décide d'utiliser le produit pour la première fois. Acte de décision/contractualisation, en amont de tout usage réel. Un acteur acquis n'est **pas** un acteur actif. Agnostique : ne plus réserver le terme à RDV-I.
- Niveau institutionnel : l'org signe / donne le feu vert.
- Niveau individuel : le compte agent est créé.

| Produit | Définition opérationnelle |
|---|---|
| RDV-Insertion | Convention / contrat de sous-traitance des données CD signée |
| Dora | Référencement d'un GT |
| Mon Récap | Structure commande un carnet |
| Les Emplois | Conventionnement SIAE |
| Le Marché | Inscription structure |

### Activation

**Général** — Passage du compte créé au **1er acte métier réalisé**. Le seuil est l'acte métier, jamais la connexion.
`taux d'activation = utilisateurs ayant réalisé >=1 acte métier / utilisateurs créés`
- Niveau institutionnel = **Déploiement** : embarquement réussi (paramétrage, formation, import initial, montée en charge, 1er acte métier de l'org). Étape qui peut s'enliser. Ne pas employer « déploiement » pour la distribution physique de carnets (Mon Récap → « distribution »).
- Niveau individuel : l'agent réalise son 1er acte métier (pas une simple connexion).

| Produit | Définition opérationnelle |
|---|---|
| RDV-Insertion | 1er RDV honoré |
| Dora | 1ère iMER |
| Mon Récap | Carnet distribué |
| Les Emplois | 1ère offre publiée |
| Le Marché | 1ère offre diffusée |

### Rétention

**Général** — Sur une cohorte active en N, part encore active en N+1. Critère d'activité = acte métier (pas retour sur le site). Synonyme : **Adoption** (usage régulier installé). Distinguer adoption **organisationnelle** (l'institution intègre le produit) et **individuelle** (l'agent l'intègre dans ses pratiques).
`rétention = actifs en N et N+1 / actifs en N`
- 2 dimensions à ne pas confondre : **persistance** (ne pas perdre l'utilisateur) et **profondeur** (intensifier son usage — voir *Mesures de profondeur*).

| Produit | Définition opérationnelle |
|---|---|
| RDV-Insertion | Agent >=1 RDV/mois ; CD >=1 participation/mois |
| Dora | Utilisateur >=1 iMER/mois |
| Mon Récap | à définir |
| Les Emplois | à définir |
| Le Marché | à définir |

### Référence

**Général** — Un acteur en amène d'autres : CD qui en convainc un autre, agent qui forme ses collègues, GT ambassadeur. Étape à part entière du funnel, **aujourd'hui non mesurée**.
- Niveau institutionnel : l'org en convainc une autre (CD ambassadeur).
- Niveau individuel : l'agent prescrit l'outil à ses collègues.

| Produit | Définition opérationnelle |
|---|---|
| RDV-Insertion | CD ambassadeur (non mesuré) |
| Dora | GT ambassadeur (non mesuré) |
| Mon Récap | Bouche à oreille |
| Les Emplois | Non mesuré |
| Le Marché | Non mesuré |

### Impact

**Général** — Combien d'actes métiers l'acteur génère. C'est le **North Star** du funnel : volume d'actes métiers (générés par l'org / réalisés par l'agent).

| Produit | Actes métiers |
|---|---|
| RDV-Insertion | RDV orientation/accompagnement, entretien SIAE |
| Dora | iMER, orientation |
| Mon Récap | Distribution + remplissage carnet |
| Les Emplois | Candidature, recherche offre |
| Le Marché | Diffusion offre, MAJ fiche |

## Concepts transverses

- **Acte métier** — Action à valeur métier au bénéfice direct ou indirect d'un bénéficiaire. **Unité de compte centrale, North Star = l'Impact du funnel.** 2 catégories : accompagnement (action directe) et support (prépare/facilite). Source de vérité de la liste : `knowledge/stats/actes-metier.md`. Règle North Star : **70 jours** de délai de consolidation.
- **Utilisateur actif** — A réalisé **>=1 acte métier** sur la période de référence (mois calendaire). La définition « >=1 connexion » est explicitement déclassée (proxy web inflationniste).
- **Funnel** — La séquence AARRI elle-même. Un funnel = instanciation produit du AARRI à un niveau (institutionnel ou individuel). Les funnels détaillés par produit vivent en couche 2.
- **Taux de conversion / transformation** — Passage d'une étape AARRI à la suivante. Convention : « **conversion** » pour les funnels web (clic, commande), « **transformation** » pour les funnels B2B institutionnels (CD vers acquisition). Toujours documenter numérateur et dénominateur.

## Mesures de profondeur (sous-dimensions de la Rétention)

- **Intensité d'usage** — Volume/fréquence d'actes métiers par utilisateur actif sur la période. Intensifier = faire réaliser plus d'actes métiers.
- **Diversité d'usage** — Nombre de types d'actions distincts utilisés. Indicateur avancé de maturité d'appropriation.
- **Power user** — Décile supérieur combiné intensité + diversité. À fixer comme top 10 % sur un score composite (intensité × diversité), une fois le score défini. Pas de définition par volume seul.
- **Engagement** — Indicateur composite = persistance + intensité + diversité. **Ne pas** le mesurer en actions/visite web (proxy purement comportemental).
- **Maturité (acteur / territoire)** — Score d'appropriation = ancienneté + intensité + diversité + autonomie + expertise sur les actes métiers concernés. Seule brique formalisée aujourd'hui : `rate_of_autonomous_users`.

## Mesures de marché

- **Taux de pénétration** — `actifs / marché adressable`. Dénominateur stable, à fixer par produit (couche 2). Répond à « est-ce qu'on est utilisé ? ».
- **Couverture** — Présence binaire sur un territoire/population, indépendamment de l'intensité. Répond à « est-ce qu'on est présent ? ». Ne plus l'employer pour le taux de géolocalisation des données.
- **Plafond d'acquisition** — Seuil de saturation du marché adressable. Distinguer saturation (tous les acteurs intéressés sont acquis) et blocage fonctionnel (les non-acquis ne peuvent pas adopter pour raisons réglementaires/opérationnelles).
- **Potentiel de déploiement** — Volume d'actes métiers additionnels si les non-utilisateurs s'activaient. Méthode de calcul à fixer par produit.

### Dénominateur de pénétration par produit

| Produit | Dénominateur |
|---|---|
| RDV-Insertion | 101 CDs |
| Dora | CDs/territoires potentiels (à fixer) |
| Mon Récap | Total SIAE/structures IAE |
| Les Emplois | à fixer |
| Le Marché | à fixer |
