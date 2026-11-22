# Rédiger une campagne email

## Ce que je veux

Quand un bizdev demande une campagne ou une séquence email à l'agent, je veux que l'agent suive la méthode de l'équipe growth, du cadrage jusqu'au brouillon prêt à valider. L'agent n'envoie jamais rien.

## Ce qui devra marcher

DOD-1 — Quand je demande une campagne, l'agent pose le cadrage (public, acte attendu, outil d'envoi, signataire) avant d'écrire. Si ma demande est vide ou contredit la carte de l'initiative, il s'arrête et me pose la question.

DOD-2 — L'agent compte la cible dans Attio et liste, dans Brevo, les emails que ce public reçoit déjà, avant d'écrire.

DOD-3 — Le brouillon suit le ton et le format de l'outil choisi, Brevo ou La Growth Machine, et ses liens portent le suivi de campagne.

DOD-4 — La campagne prête se dépose dans la base Notion « Campagnes à valider », avec le statut « À valider ». Rien n'est programmé ni envoyé.

## Sources lues

- `CONTRIBUTING.md` et `docs/paved-road/l0-definition-of-done.md` : format de ce fichier.
- Les skills `attio` et `brevo`, dont cette skill se sert : cette PR suit leurs deux PR.
- `.claude/rules/review.md` : aucune donnée personnelle dans le dépôt public. Les exemples de la skill sont des emails déjà partis : chaque nom de personne en est retiré avant la PR.

## Questions ouvertes

1. La base Notion « Campagnes à valider » doit être partagée avec l'intégration d'Autometa. Défaut retenu : c'est fait avant la fusion, par l'équipe growth.

## Validation

Validé par Mehdi Aïda le 2026-11-22.
