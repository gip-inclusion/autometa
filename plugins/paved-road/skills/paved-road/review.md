# Review — comparer le code au contrat

But : vérifier que le code fait ce que le contrat dit, **ni plus ni moins**, et regarder ce
qu'aucun test n'avait prévu. Tout ce qui peut faire corriger passe ici, **avant** les preuves.

Cette étape se joue dans l'état `build`. Tu n'en sors que quand la lentille n'a plus de bloqueur.

## Dans l'ordre — l'ordre compte

**1. Lancer la lentille.** Écris le diff de la branche dans `/tmp/paved-road/<slug>/diff.patch`,
puis lance le sous-agent `paved-road:design-coherence` en lui indiquant ce fichier. Il n'a que
`Read`, `Grep`, `Glob` : c'est toi qui lui fournis le diff, il ne sait pas faire de `git`.

Sa question, que personne d'autre ne pose : pour chaque `DOD-N`, quel code le réalise ? Quel code
ne se rattache à aucun critère ? Le code fait-il autre chose que ce que le critère décrit ?

**2. Traiter chaque bloqueur.** Un bloqueur, c'est un écart qui rend un critère faux, absent, ou
réalisé par autre chose que ce qu'il décrit. Pour chacun : corrige le code, **ou** écris sous le
bloqueur pourquoi ce n'en est pas un.

Puis relance la lentille. Un bloqueur que tu n'as pas adressé ne disparaît pas d'une relance — la
lentille est un sous-agent distinct, tu ne réécris pas son verdict, tu y réponds.

La boucle tourne jusqu'à ce qu'aucun bloqueur nouveau ne subsiste. Elle n'a pas de plafond. Si
elle ne converge pas, arrête-toi, dis-le au demandeur, et écris l'entrée de rétro : une boucle qui
tourne en rond est une information sur le contrat, pas sur le code.

**3. Le smoke, en dernier.** Lance `uv run --frozen python scripts/smoke.py plan`. S'il dit qu'une
interface est touchée, déroule le parcours dans le navigateur : une capture par critère, un
`rapport.md`.

Le smoke vient **après** les corrections, jamais avant : `plan` refuse une seconde passe sur la
même empreinte d'interface, donc toute correction postérieure rouvrirait une passe. Les captures
restent hors du dépôt.

**4. Avancer** : `make paved-road-advance` — il rejoue `doctor`, `make lint`, `make security`,
`make test` — puis l'état devient `prove`. Dis que l'étape est franchie, demande une nouvelle
session.

## Pourquoi la lentille bloque alors qu'aucune CI ne la rejoue

Un jugement de modèle rejoué en intégration continue clignote : vert, rouge, vert, sur le même
code. On ne peut donc pas en faire un contrôle requis. Mais laisser un avis purement consultatif
ne changerait rien à rien — sur une fonctionnalité de données, personne d'autre ne compare le code
à l'intention : les tests ne connaissent pas le contrat, le pair ne lit pas le diff, et la review
app est vide.

D'où ce régime : la lentille arrête **l'agent, en session**, jusqu'à ce que les bloqueurs soient
traités. L'intégration continue ne vérifie que la présence d'un rapport à jour, et le pair le lit
dans la PR.
