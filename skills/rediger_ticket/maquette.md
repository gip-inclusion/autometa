# Lire une maquette Figma

Le script `maquette.py` donne, pour chaque cadre, son nom, ses textes visibles et une image. **Regarde chaque image** avant d'écrire.

## Ce que la maquette apporte

| Dans la maquette | Dans le ticket |
|---|---|
| le nom de l'écran, du parcours, de la page | « Périmètre », avec le nom affiché |
| un texte nouveau ou modifié (titre, message, bouton, lien) que l'entrée ne donne pas | « Attendu », recopié tel quel, avec « (maquette) » |
| plusieurs versions (« Avant / Après », « Version de base / Choix 1 », variantes A et B) | la version cible ; si l'entrée ne dit pas laquelle est retenue, une question dans « À trancher » |
| des états (vide, erreur, selon le profil) | une puce par état |

## Ce qu'elle n'apporte pas

- Les **données d'exemple** (noms, structures, dates, e-mails, montants) : fictives ou personnelles, jamais recopiées.
- Le reste de l'écran : ne décris que ce qui change ou concerne la demande.
- Les détails visuels : l'équipe a la maquette.

## Contrôles

- La maquette correspond-elle à la demande ? Sinon, ne t'en sers pas et demande : « Le lien Figma montre <ce qu'il montre> : est-ce le bon cadre ? »
- Contradiction entre l'entrée et la maquette : l'entrée prime ; signale l'écart dans « À trancher ».
- Lien non lu (sans node-id, accès refusé) : garde le lien et demande un lien vers le cadre.
