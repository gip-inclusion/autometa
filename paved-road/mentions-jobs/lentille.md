# Lentille design-coherence — 2026-11-04

Deux passes. Un bloqueur à la première, corrigé ; aucun à la seconde.

**BLOQUEUR (passe 1) — DOD-1, la dernière sortie réussie cherchée parmi les trois runs listés
seulement** — corrigé. Un job dont les trois derniers runs avaient échoué n'affichait aucune sortie,
même quand un run plus ancien avait réussi. Les 20 runs chargés servent désormais à trouver la
dernière sortie réussie ; trois seulement sont listés. Test
`test_dod_1_last_success_found_beyond_the_three_listed_runs`.

Remarques, et ce qui en a été fait :

- **DOD-3, réponse malformée du service de jobs** — en partie corrigé : une réponse non JSON
  (`ValueError`) est absorbée comme une panne, le message part sans contexte. Un pipeline sans
  `name` ou sans `id` reste traité en cas impossible et lève.
- **Effet de bord du déplacement de l'appel avant l'enregistrement du message (passe 2)** —
  retiré. Ce déplacement, tenté en passe 1 pour qu'un échec ne laisse pas la conversation marquée
  en cours, ouvrait une fenêtre où deux envois franchissaient le contrôle « conversation déjà en
  cours ». L'appel reste à sa place d'origine, juste avant l'envoi au runner.
- **Horizon de 20 runs pour la dernière sortie réussie** — conservé, le texte transmis à l'agent
  le dit (« aucun run réussi parmi les 20 derniers »).
- **Deux « User request: » dans une conversation knowledge qui mentionne un job** — conservé, sans
  effet sur un critère : le contexte du job reste un bloc délimité.
- **Syntaxe plus tolérante côté serveur que la liste d'autocomplétion** (`(@nom` reconnu, liste
  ouverte seulement après un espace) — conservé, sans effet sur `DOD-5`.
- **Liste plafonnée à 8 noms, rappel du coût d'une relance** — conservés. Le rappel du coût reprend
  la règle de confirmation du skill `compose_and_launch_job`.
