# Align — transformer un besoin en contrat jugeable

But : produire `paved-road/<slug>/definition-of-done.md`, une liste de critères en français qu'une
personne non technique peut lire et valider, et sur lesquels elle jugera la PR.

## Dans l'ordre

**1. Ouvrir le parcours.** Crée la branche `<auteur>/feat/<slug>` — le slug donne aussi le nom du
répertoire sous `paved-road/`. Lance `make paved-road-start FEATURE=<slug>`.

**Si ta branche ne part pas de la branche principale publiée**, ajoute `BASE=<branche de départ>` :
`make paved-road-start FEATURE=<slug> BASE=<branche>`. Sans elle, le contrôle du contrat juge ton
parcours sur les commits de la branche dont il part, et refuse en annonçant que du code a été
committé avant le contrat — alors que le contrat est bien ton premier commit. `git log --oneline -1
<branche>` te dit d'où tu pars si tu as un doute.

`start` installe au passage les hooks que le worktree n'a pas et lance le diagnostic
d'environnement. Lis ce qu'il affiche : ce qui n'est pas en ordre y figure, avec le geste qui le
répare. Une panne d'environnement est de famille B — elle s'annonce au demandeur avec ce geste,
jamais avec un nom de fichier.

**2. Lire avant d'écrire.** Six règles, dont les deux premières sont inconditionnelles :

- **R1** — le code existant de la surface touchée. Tu ne peux pas écrire un critère sur un écran
  que tu n'as pas lu.
- **R2** — toute valeur chiffrée que tu écris cite sa source de mesure. Pas de « environ 300 »
  sorti de nulle part.
- **R3** — le glossaire métier (`knowledge/bizdev/glossaire.md`) pour les termes IAE.
- **R4** — `lib/dashboard_api.py` si la demande touche un tableau de bord.
- **R5** — les décisions déjà prises : `docs/plans/`, les DoD des parcours précédents.
- **R6** — l'usage réel : ce que les gens font vraiment, pas ce qu'on suppose.

L'exploration lourde se délègue à un sous-agent de lecture, pour ne pas saturer ton contexte.

**3. Écrire les critères.** Un critère décrit **un résultat observable, au présent**, du point de
vue de quelqu'un qui utilise le produit.

Chaque `DOD-N` cite entre crochets la phrase du brief qu'il réalise :

```
DOD-1 — [du brief : « télécharger en markdown »] quand je clique sur Télécharger, un fichier
.md se télécharge, au lieu de s'afficher dans un onglet.
```

Un critère sans phrase de brief rattachable est suspect : remonte-le au demandeur au lieu de
l'inventer.

Ce qui n'est **pas** un critère : un invariant permanent (« le code passe le lint », « pas de SQL
non paramétré »). Ça, c'est un garde-fou, il vaut pour tout le dépôt et il est déjà vérifié
ailleurs. Un critère est propre à cette demande.

**4. Chasser les trous.** Lance le sous-agent `gap-hunter`. Pour chaque critère il cherche l'entrée
vide, le doublon, la valeur hors limites, l'état initial absent, l'accès concurrent. Ce qu'il
trouve devient un `DOD-N` de plus, **avec une réponse par défaut déjà choisie** — jamais une
question de plus au demandeur.

**5. Soumettre.** Au plus **cinq décisions**, chacune avec sa réponse recommandée et sa conséquence
observable. Toutes en une fois, pas au fil de l'eau. Ne pas répondre, c'est accepter le défaut.

Ce que le demandeur ne voit pas : la section « Sources lues », qui cite des fichiers. Elle est
pour toi et pour un owner qui voudrait aller au fond.

Pas de question technique. Pas de question dont la réponse ne change rien d'observable. « Faut-il
découper en plusieurs commits ? » n'est pas une question pour le demandeur.

**6. Enregistrer la validation** — qui a validé, quand — dans la section « Validation ».

**7. Committer la DoD en premier.** C'est le **premier commit de la branche**, avant toute ligne de
code. C'est la seule chose qui distingue un accord passé d'avance d'un contrat écrit après coup
pour coller au code produit. La description de PR affichera les deux dates côte à côte.

**8. Avancer** : `make paved-road-advance`. Si `verify_dod` passe, l'état devient `build`. Dis au
demandeur, en français, ce que le contrat promet, et attends son feu vert avant d'écrire la
première ligne de code. Reste dans la même session.

## Si le besoin est trop flou pour cinq décisions

Ce n'est pas un échec, c'est une information. Dis-le, propose de découper en deux parcours, et
laisse le demandeur choisir. Un contrat qu'on ne sait pas écrire est un contrat qu'on ne saura pas
juger.
