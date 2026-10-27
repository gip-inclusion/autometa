# Lentille design-coherence — 2026-10-12

Première passe : trois bloqueurs, huit remarques. Chaque bloqueur est corrigé ; les remarques sont
corrigées ou justifiées ci-dessous.

## Bloqueurs

**BLOQUEUR — DOD-2 : l'adresse d'un site n'est jamais vérifiée.** La branche avait corrigé les
adresses de Pilotage et de Dora dans le tableau des sites sans toucher `knowledge/sites/dora.md` ni
`knowledge/sites/pilotage.md`, et rien ne le voyait.
Corrigé : `site_conflicts` refuse désormais, en prose, l'autre forme d'une adresse du tableau (avec
ou sans `beta.`). Le code en ligne est exempté, parce qu'il cite des données (définitions de
segments Matomo, pages vues) qui portent légitimement l'ancienne adresse. Cinq occurrences
trouvées et corrigées (deux fiches de site, la fiche Dora, deux données de `marche.md` passées en
code). Test : `test_dod_2_un_site_contredisant_le_tableau_des_sites_est_refuse` (cas d'adresse),
`test_dod_2_une_ancienne_adresse_citee_comme_donnee_passe`.

**BLOQUEUR — DOD-4 : la règle de priorité reste recopiée dans des skills, en phrases courtes.**
Corrigé dans le contenu : la description et l'introduction du skill `autometa_tables_db` et la
ligne de `publish_dataset` ne la reformulent plus, elles renvoient à `AGENT.md`. Ajout du test
manquant sur le second jeu de règles (`test_dod_4_une_regle_de_choix_des_tables_recopiee_est_refusee`).
Justification de ce qui reste : aucune règle déterministe ne reconnaît une **paraphrase** courte
d'une règle — c'est précisément ce que le design réserve à la lentille `knowledge-drift`. Le
contrôle attrape la copie (y compris retouchée) d'une phrase d'au moins huit mots ; une phrase plus
courte (« Priorité absolue sur Metabase. ») apparaît légitimement dans un renvoi. Écrit dans la PR
comme limite.

**BLOQUEUR — DOD-8 : le tableau des dépôts GitHub se contredisait (main / staging).**
Corrigé : la colonne s'appelle « Branche par défaut » et porte `staging` pour `pilotage` et
`rdv-insertion`. Les sept dépôts ont été interrogés par l'API GitHub le 2026-10-12 (branche par
défaut, existence de `main`, redirection 301 de `master`), pas seulement les trois cités dans la
DoD — la DoD ne se réécrit pas après validation, la PR le dit.

## Remarques

- **DOD-2, instance Metabase sur plusieurs lignes** — corrigé : la recherche porte sur le texte
  entier, testée sur les deux formes.
- **DOD-1, fonction citée en prose** (`` `X` dans `lib/y.py` ``) — non contrôlé, justifié : relier
  un identifiant en prose au module voisin sur la ligne produit des faux positifs (noms de colonnes,
  de paramètres). Les imports sont contrôlés ; la prose reste à la relecture. Limite écrite dans la PR.
- **DOD-6, la fiche Dora sautait `raw_dora`** — corrigé : la route cite `raw_dora` avant le Metabase
  Dora, et dit que les copies de tables dans `raw_dora` sont à confirmer dans le catalogue.
- **DOD-7, ordre et signalement conditionnel** — signalement rendu inconditionnel. Les rangs
  « ce fichier » et `CLAUDE.md` ajoutés à l'ordre du contrat découlent de DOD-4 (une seule maison
  pour les règles) ; l'ordre relatif catalogue > skill > fiche est celui du contrat.
- **DOD-9, portée** — trois points. (1) Les tables citées en prose ou en tableau ne sont pas
  contrôlées : seul un bloc SQL dit sans ambiguïté « ceci est une table » ; (2) une fiche à
  plusieurs sources n'est contrôlée que quand toutes ont un instantané, faute de pouvoir rattacher
  une table non qualifiée à une source — l'en-tête le rend visible (la fiche est signalée) ;
  (3) `appli_monrecap_db` — corrigé, le skill est désormais reconnu comme source de base.
- **DOD-3, `verifie_le` initialisé à la date du dernier commit** — assumé et écrit dans la PR : pour
  les fiches non relues dans cette branche, c'est la seule date disponible, et elle peut être plus
  récente que la vraie vérification. Seule `knowledge/dora/README.md` porte une date de vérification
  réelle (confrontée au code Dora le 2026-10-12).
- **Excès** — la liste des produits de la ligne Bizdev (`AGENT.md`) aligne le nom du produit sur
  `CLAUDE.md` (dérive de nommage, DOD-8) ; la note « 403 » de l'instance Dora (`metabase_query`)
  est l'incohérence N11 (repli impossible sur cette instance, DOD-8) ; la consigne iMER « toujours
  … et demander d'abord » se contredisait elle-même dans la fiche, elle est réduite à son défaut
  (présenter l'iMER) — DOD-8.
- **DOD-8, « versions de tables de référence »** — `structures_v0` (Metabase Stats) contre
  `structures_v1` (`autometa_tables_db`) : ce n'est plus une contradiction une fois le périmètre
  déclaré (`metabase:stats` contre skill de la base centrale) ; la vérification réelle attend
  l'instantané du catalogue. Listé dans la PR.

## Seconde passe — 2026-10-12

Les trois bloqueurs sont levés, vérifiés dans les fichiers ; aucun nouveau bloqueur. Deux remarques :

- **Contrôle d'adresse étroit** — il ne voit que l'ajout ou le retrait de `beta.` sur une adresse en
  `.gouv.fr`, hors code en ligne. C'est la forme réelle des dérives trouvées ; une adresse sans
  rapport ou écrite en code passerait. Écrit dans la PR comme limite.
- **Drapeau `re.S` sans effet** sur le motif des instances Metabase — retiré.
