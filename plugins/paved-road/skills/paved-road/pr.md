# PR — donner à juger

But : une pull request qu'une personne qui ne lit pas le code peut approuver en conscience.

## Dans l'ordre

**1. Vérifier que tout est là** : la definition of done, le journal, les attestations, le rapport
de la lentille, la rétro. Puis `make paved-road-status` pour confirmer qu'aucun critère ne traîne.

**2. Ouvrir la PR** avec `gh pr create`, en remplissant le gabarit du dépôt
(`.github/pull_request_template.md`) :

- **Ce que je voulais** — une phrase, dans les mots du demandeur ;
- **Ce qui devait marcher** — le tableau des critères, verdict et lien vers la preuve. Reprends la
  sortie de `make paved-road` plutôt que de le composer à la main ;
- **Ce qui n'a pas été démontré** — et pourquoi. « Rien » est une réponse valable, écris-la ;
- **Pour juger sans lire le code** — l'URL de la review app, les captures du smoke, ce que la
  lentille a signalé et ce que tu as corrigé, la date du premier commit du contrat et celle du
  premier commit de code ;
- **Ce que cette PR change dans l'outillage** — « rien » la plupart du temps. Sinon, en français,
  ce que la machinerie fait de différent, et tout garde-fou affaibli.

Le titre et la description sont en français. Les messages de commit restent en anglais.

**3. Écrire la rétro** : `paved-road/<slug>/retro.md`. Court, en prose, sans gabarit à cases. Ce
qui a frotté, ce qui a surpris, ce qui t'a fait perdre du temps, et le coût du parcours (`/cost`).
C'est ce qui fait évoluer le dispositif : une friction qui revient devient un contrôle.

**4. Le dire au demandeur**, en français, avec le lien. Précise ce qu'il doit regarder : les
critères, la review app, les captures. Pas le diff.

## Ce que tu ne fais pas

**Tu ne poses aucun label**, et surtout pas `break-glass` : il lève le seul contrôle qui vérifie
tes preuves. Si tu penses qu'il en faut un, demande-le, explique pourquoi, laisse un humain le
poser.

**Tu ne pousses plus après l'approbation** sans le dire. Un push après le « oui » du pair rouvre la
question qu'il venait de trancher.

**Tu ne fusionnes pas.** C'est le pair qui appuie sur le bouton.

## Ce que le pair doit savoir, et que tu lui rappelles

- Une review app part d'une **base vide** : pour une fonctionnalité de données ou de tableau de
  bord, il n'y aura rien à cliquer. Dis-le, sinon il croira que c'est cassé.
- Si la PR touche une zone critique ou l'outillage, son approbation ne suffira pas : un owner
  devra consentir aussi. Il n'est pas plus technique que lui ; s'il ne se sent pas de juger, c'est
  à lui d'aller chercher quelqu'un qui l'est.
- Du code daté **avant** le contrat, on ne signe pas : on va d'abord chercher un avis technique.

## Si `main` bouge avant la fusion

Le dépôt exige une branche à jour. Rebase, puis regarde le contrôle « Ce qui devait marcher » : si
les empreintes ont bougé, les preuves sont périmées et il faut les refaire (`prove.md`). Annonce-le
plutôt que de laisser le pair découvrir un rouge après son approbation.
