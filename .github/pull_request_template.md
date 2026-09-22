## Ce que je voulais

<!-- Une phrase, dans les mots du demandeur. Pas de vocabulaire technique. -->

## Ce qui devait marcher

<!--
Une ligne par critère de la definition of done, avec son verdict et le lien vers la preuve.
Le tableau est produit par le parcours ; ne pas le remplir à la main.

| Critère | Ce qui devait marcher | Verdict | Preuve |
|---|---|---|---|
| DOD-1 | … | démontré | `paved-road/<slug>/attestations/DOD-1.md` |
-->

## Ce qui n'a pas été démontré

<!-- Les critères sans preuve, et pourquoi. « Rien » est une réponse valable — l'écrire. -->

## Pour juger sans lire le code

- **Review app** : <!-- URL de l'encart de déploiement, une fois la CI verte. Base vide : pour une
  fonctionnalité de données, il n'y aura rien à cliquer, le dire ici. -->
- **Captures du smoke** : <!-- si une interface est touchée -->
- **Relecture `design-coherence`** : <!-- ce que la lentille a signalé, et ce qui a été corrigé -->
- **Premier commit du contrat** : <!-- date --> · **premier commit de code** : <!-- date -->

> Règle de lecture pour le pair : du code daté **avant** le contrat, on ne signe pas — on va
> d'abord chercher un avis technique.

## Ce que cette PR change dans l'outillage

<!--
Rien, la plupart du temps — écrire « rien ».
Sinon : ce que la machinerie fait de différent, en français, et tout garde-fou affaibli
(seuil abaissé, test supprimé, assertion changée, route sans authentification).
Une PR qui touche une zone critique ou l'outillage demande aussi le consentement d'un owner.
-->

---

<sub>Parcours et attendus : `CONTRIBUTING.md`. Conception : `docs/plans/2026-08-22-paved-road-workflow.md`.</sub>
