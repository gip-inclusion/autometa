# Lentille design-coherence — rapport et réponses

Deux passes, le 2026-09-18, par un sous-agent en lecture seule, sur le diff de la branche contre
`origin/main` (code inchangé entre les deux passes : seul le contrat a bougé). Le sous-agent signale
avoir lu par `grep`/`head` en plus de Read, sans rien écrire.

## Passe 1 — sur le contrat `DOD-1` à `DOD-7`

**BLOQUEUR — DOD-6 : la consigne permet de donner l'adresse d'un tableau de bord cassé.** Le critère
disait « corrige jusqu'à obtenir un verdict positif », l'intention « ne doit plus donner l'adresse
d'un tableau de bord cassé » ; le skill `verify_dashboard` dit « livrer quand même le TDB mais le
signaler explicitement ».

> **Réponse.** Le code n'est pas modifié : c'est le contrat qui décrivait mal la conduite voulue.
> `DOD-6` porte désormais la conduite « livrer, annoncer l'échec, lister les défauts » ; l'intention
> dit « … cassé sans le dire » ; le choix bloquer / informer est soumis à Alexis (Décision 2), avec
> « informer » par défaut. L'amendement a eu lieu avant le premier commit du contrat.

Remarques (non bloquantes) :

- `DOD-3` partiel : l'examen « série sans aucune valeur » ne vaut que pour Chart.js ; D3 / Plot sont
  jugés sur la seule présence de tracés (limite documentée dans le skill). Un graphique sans `id`
  est nommé `<canvas>` / `<svg>` seulement.
- `DOD-5` : un chargement qui dépasse 30 s, une URL injoignable ou une erreur de lecture du canvas
  sortent en « audit impossible » avec le conseil trompeur « Navigateur absent ? » (→ Décision 4).
  Une URL cible en 404 rend un verdict négatif plutôt que « introuvable ». Une exception imprévue
  sortirait en code 1, le même que « verdict négatif », mais sans JSON.
- `DOD-7` (première version) : l'avertissement sur `/api/…` s'applique aussi sur l'application
  servie (→ reporté sur `DOD-8`, voir passe 2).
- Excès sans critère, bénins : `Dockerfile`, `pyproject.toml`, `uv.lock` (dépendances techniques de
  `DOD-1`/`DOD-5`) ; `serve()` (nécessaire pour `data.json`) ; message de `scripts/doctor.py`
  (outillage de poste) ; deux lignes du Session Ledger de `CLAUDE.md`.

## Passe 2 — sur le contrat `DOD-1` à `DOD-10`

Bloqueur de la passe 1 **levé** : « le code et le contrat disent désormais la même chose ; le fond
reste à trancher par un humain, et c'est bien là qu'il est placé ». `DOD-9` et `DOD-10` décrivent
fidèlement le code. **Aucun bloqueur.**

Remarques :

- `DOD-8` : « pour le vérifier en entier, on le vérifie à l'adresse de l'application » était faux —
  un `/api/query` en 500 reste un avertissement quelle que soit la cible.
  > **Réponse.** Corrigé dans le contrat par une révision datée sous `DOD-8`, à revalider. Faire
  > compter ce refus comme une erreur quand l'application est servie est une amélioration de code
  > laissée à un parcours suivant.
- `DOD-8` : un graphique jamais créé faute de données ne fait échouer que si le nombre attendu est
  donné (→ Décision 3) ; un Chart.js à `datasets: []` dessine ses axes et passe. Laissé en limite,
  annoncé dans la PR.

## Smoke

`scripts/smoke.py plan` : aucun chemin d'interface (`web/templates`, `web/static`, `web/routes`)
modifié — smoke non requis.
