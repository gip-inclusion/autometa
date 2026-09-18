# Lentille gap-hunter — rapport et suites données

Lancée le 2026-09-18 sur la première version du contrat (`DOD-1` à `DOD-7`). Sous-agent en lecture
seule ; il signale lui-même avoir lu par `cat`/`grep` plutôt que par Grep/Glob, sans rien écrire.

## Trous trouvés, et ce qu'ils sont devenus

| Proposé | Trou | Suite |
|---|---|---|
| DOD-8 | TDB de chiffres clés, sans graphique | Devenu `DOD-9` (comportement actuel : verdict positif + avertissement) |
| DOD-9 | Nombre de graphiques attendus oublié → un TDB sans graphique passe | Décision 3 soumise à Alexis (défaut : inchangé dans cette PR) |
| DOD-10 | Page lente : diagnostic « navigateur absent ? » trompeur ; données lentes → « rendu vide » sans cause | Décision 4 (défaut : inchangé, amélioration renvoyée à un parcours suivant) |
| DOD-11 | Graphiques masqués (onglet inactif) non vérifiés, en silence | Décision 5 (défaut : inchangé, amélioration renvoyée) |
| DOD-12 | Table très large défilant dans son cadre | Devenu `DOD-10` (comportement actuel) |
| DOD-13 | Erreur non corrigeable : `DOD-6` contredisait la conduite du skill | `DOD-6` amendé avant commit ; Décision 2 soumise |
| DOD-14 | Vérification par URL qui tombe sur la page de connexion | Non retenu comme critère : non vérifié dans le code, noté dans « Ce qui n'a pas été démontré » de la PR |
| DOD-15 | Deux vérifications simultanées écrasent la même capture | Non retenu : effet visible seulement pour l'agent, pas pour le demandeur ; noté dans la rétro |

`DOD-7` initial (« pas de visite comptée » + « appels à l'application en avertissement ») était mal
formé : la seconde moitié promettait un avertissement là où l'utilisateur voit un échec (graphiques
vides). Scindé en `DOD-7` (visite) et `DOD-8` (données en direct : avertissement sur les demandes,
échec si les graphiques restent vides).

Rien d'autre n'est à signaler : le premier usage sans navigateur est couvert par `DOD-5`, les
légendes masquées de Chart.js sont déjà bien traitées.
