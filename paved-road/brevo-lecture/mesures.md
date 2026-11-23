# Mesures — DOD-3

DOD-3 demande que le compte des envois par modèle, pour un compte qui envoie 30 000 emails par mois, arrive en moins de 10 secondes. L'attestation `attestations/DOD-3.md` rejoue les tests `dod_3` contre un Brevo simulé : elle prouve le comportement (compte par modèle, fenêtre de 30 jours, plafond à 90, troncature signalée), pas le temps de réponse. Le temps a été mesuré à la main.

## Méthode

Le 2026-11-22, sur les trois comptes réels, avec leur clé de lecture : un appel de `BrevoClient(<compte>).sends_by_template(30)`, chronométré de l'appel au retour, depuis un poste de développement.

## Résultats

| Compte | Envois sur 30 jours | Temps |
|---|---|---|
| marketing | 179 | 0,2 s |
| emplois | 13 026 | 1,5 s |
| dora | 30 069 | 4,1 s |

Le compte DORA est celui qui approche les 30 000 envois du critère : la réponse arrive en 4,1 s, sous la borne de 10 s. Aucune sortie ne contenait de « @ ».

Ces temps dépendent de Brevo et du réseau. Ils ne se rejouent pas en CI, qui n'a pas de clé.
