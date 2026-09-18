# Lentille design-coherence

Rapports du sous-agent `design-coherence`, reproduits tels quels ; les réponses de l'agent sont
signalées « Réponse ».

## Passe 1 — sur `b307e28`

Deux bloqueurs (DOD-9, DOD-4), douze critères réalisés.

Par critère : DOD-1, 2, 3, 5, 6, 7, 8, 10, 11, 13, 14 réalisés ; DOD-4 et DOD-9 partiellement
réalisés.

### BLOQUEUR — DOD-9 : un tableau de bord en données en direct ne peut en pratique jamais obtenir « réussi »

> Le critère dit que les lectures en direct « ne font pas échouer le verdict : elles sortent en
> avertissement », et la décision 2 le motive par « sinon ces tableaux de bord ne pourraient jamais
> obtenir réussi ». Le code ne rétrograde en avertissement que la requête elle-même. Le serveur local
> répond au `POST /api/query` par une 501 au corps HTML ; le modèle documenté fait
> `return response.json()` sans `try` : une `SyntaxError` non rattrapée remonte en `pageerror`, donc
> en erreur, et le verdict échoue. Un tableau de bord qui rattrape l'erreur affiche son bloc `#error`
> (DOD-10), laisse son graphique vide (DOD-4) ou « Chargement… » visible. Le test de DOD-9 ne vérifie
> que `judge` sur une observation fabriquée. Le comportement promis par la décision 2 n'est pas obtenu.

**Réponse — le contrat s'était trompé, révisé.** Aucune donnée ne peut être inventée pour une page
live hors de l'application, et la servir avec une session est une autre fonctionnalité. `DOD-9` porte
désormais une révision datée : la lecture elle-même sort en avertissement, ses conséquences à
l'écran restent signalées, et les consignes du skill disent à l'agent de ne pas consommer de
tentative dessus et de donner le lien en précisant que les données en direct n'ont pas été vues.
Question remontée au demandeur : faut-il, plus tard, vérifier ces tableaux de bord contre
l'application servie, avec une session dédiée ?

### BLOQUEUR — DOD-4 : le graphique vide typique du gabarit n'est pas détecté

> Un `canvas` compte comme tracé dès un pixel non transparent, un `svg` dès un `path`, `line` ou
> `text`. Or un graphique Chart.js aux séries vides ou pleines de `NaN` dessine quand même axes et
> grille ; un Plot ou un D3 vide dessine ses axes. Tous passent pour tracés. Le test navigateur
> utilise un canvas brut sans bibliothèque et ne peut pas révéler l'écart.

**Réponse — corrigé.** Pour un canvas Chart.js, le jugement porte sur les séries (au moins une
valeur finie) ; pour un `svg` Observable Plot, sur les marques de données (groupes `aria-label` hors
axes, grille et cadre) ; le comptage de pixels ne reste que pour un canvas sans bibliothèque. Deux
tests navigateur (`test_dod_4_a_chart_library_drawing_only_its_axes_is_caught[chartjs|plot]`)
reproduisent ce que ces bibliothèques laissent dans la page. Limite assumée : un graphique D3 écrit
à la main reste jugé sur la présence de formes, axes compris.

### Remarque — DOD-4 / DOD-13 : le compte inclut les pictogrammes de plus de 32 px et exclut les onglets inactifs

**Réponse.** Le second point est corrigé dans le skill : `--expect-charts` compte les graphiques
visibles au premier affichage. Le premier est assumé : un décor `svg` de plus de 32 px peut masquer un
graphique manquant ; le cas est rare dans les tableaux de bord du gabarit.

### Remarque — DOD-12 : `networkidle`, `evaluate` sans délai, `getImageData` sur canvas contaminé

**Réponse.** Le canvas contaminé est corrigé (il est jugé tracé au lieu de faire planter la
vérification). `networkidle` est assumé : un tableau de bord qui interroge en boucle sera signalé
« délai dépassé », ce qui est une information utile sur un TDB censé lire un `data.json`. Une boucle
JavaScript infinie après chargement reste non bornée : noté pour la rétro.

### Remarque — DOD-9 : la règle `/api/` ne regarde pas l'hôte

**Réponse.** Assumé : une ressource de CDN sous `/api/` est improbable.

### Remarque — excès justifiés (`/common/`, toute réponse ≥ 400)

**Réponse.** Aucune action.
