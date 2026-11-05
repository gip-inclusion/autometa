# Règles de tri des avis BOAMP

Fichier de travail de l'agent veille-boamp, versionné par Autometa. L'agent le relit à chaque run
et peut en rendre une version revue (voir « Faire évoluer ces règles »).

Toutes les comparaisons se font sur l'objet et les descripteurs mis en minuscules et sans accents.

## 1. Termes autoportants

Un avis dont l'objet porte l'un de ces termes est retenu, sauf exclusion (section 3) :

- insertion par l'activite economique, iae, siae
- structure d'insertion, structures d'insertion, entreprise d'insertion
- chantier d'insertion, chantiers d'insertion, atelier et chantier d'insertion, ateliers et chantiers d'insertion
- marche reserve
- beneficiaires du rsa, allocataires du rsa
- parcours d'insertion, accompagnement socio-professionnel, insertion professionnelle
- retour a l'emploi, demandeurs d'emploi
- plateforme de l'inclusion
- clause d'insertion, clauses d'insertion : seulement pour un marché de services

## 2. Outil numérique qualifié par un thème

Sinon, un avis est retenu si son objet désigne un outil numérique ET porte un terme de thème.

Outil numérique : logiciel, progiciel, plateforme, application, solution numerique, systeme
d'information, outil de suivi, dematerialisation, ou un descripteur Logiciel ou Informatique.

Thème : insertion, emploi, rsa, allocataire, beneficiaire, usager, accompagnement, orientation,
social, sociale, solidarite, handicap, jeunes, mission locale, france travail.

## 3. Exclusions

Un avis retenu par la section 1 ou 2 est écarté si son objet relève du bâti ou de l'environnement
physique : travaux, batiment, construction, maitrise d'oeuvre, amenagement, voirie,
assainissement, renovation, rehabilitation, espaces verts, nettoyage, gardiennage, restauration
collective, vehicule ; ou s'il ne porte que sur la protection des données : dpo, rgpd.

## 4. Rubriques

Les rubriques sont posées par le classificateur d'Autometa après le run, sur chaque avis :

- Outils numériques (étiquette outils-numeriques) : l'avis achète un logiciel, une plateforme, une
  application ou un service numérique, quel que soit son public.
- Prestations d'insertion et d'accompagnement (étiquette prestations-insertion) : l'avis achète
  une prestation d'insertion, d'accompagnement vers l'emploi ou de suivi de personnes en parcours.

Un avis peut porter les deux étiquettes, ou aucune s'il a passé le filtre pour une autre raison.

## Faire évoluer ces règles

Rends une version entière de ce fichier seulement si la lecture des avis de la semaine montre un
terme récurrent qui manque, ou une exclusion qui écarte à tort des avis pertinents. Garde la
structure, et ajoute en bas une ligne datée qui dit ce qui a changé et pourquoi.

## Journal des changements

- 2026-11-05 : version initiale, reprise de la règle de tri de la consigne du 04/11.
