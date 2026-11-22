# Lentille design-coherence — 2026-11-22

Deux passes. Trois bloqueurs à la première, un à la seconde, tous corrigés.

**BLOQUEUR (passe 1) — DOD-1, total faux au-delà de 20 000 enregistrements** — corrigé. `count` lit au plus 40 pages de 500 et rend désormais `complet: false` quand il atteint ce plafond : le total est alors un minimum, et la skill comme la documentation le disent. Test `test_dod_1_count_says_when_it_stopped_at_the_page_cap`.

**BLOQUEUR (passe 1) — DOD-5, route d'Attio choisie par un paramètre** — corrigé. `object`, `attribute` et `list` entrent dans le chemin de l'URL : une valeur comme `people/records?x=` visait la route de création. Ces trois paramètres doivent être des slugs entiers (`fullmatch`), et chaque paramètre est contrôlé en type avant tout appel. Cas testés dans `test_dod_5_unplanned_requests_are_refused_before_any_call`, avec un retour à la ligne final relevé en passe 2.

**BLOQUEUR (passe 1, puis passe 2) — DOD-5, refus qui ne disent pas ce qui est permis** — corrigé. Un paramètre inconnu ou manquant fait lister les paramètres permis, une valeur refusée dit ce qui est attendu (un slug, un entier, un objet JSON, une liste), et `/api/query` sans méthode liste les méthodes. Tests `test_dod_5_refused_parameter_lists_the_allowed_ones` et `test_dod_5_refused_value_says_what_is_expected`.

Remarques, et ce qui en a été fait :

- **DOD-4, retrait par type d'attribut** — corrigé. Un email ou un numéro français saisi dans un attribut texte est retiré aussi. Une lecture réelle de 200 structures ne rend aucune adresse ; le seul « @ » restant est le nom d'un compte de réseau social dans une description.
- **DOD-4, un filtre peut tester si un email est dans le CRM** — corrigé : un filtre qui porte sur un email ou un téléphone est refusé.
- **Choix plus strict que la DoD** — conservé. L'agent reçoit lui aussi les contacts sans email ni téléphone : DOD-2 n'en a pas besoin, et la skill `campagne_email` compte une cible sans liste nominative.
- **DOD-2, `records` coupe à 500 sans le dire** — conservé, le critère dit « 500 au plus ».
- **DOD-3, `entries` coupé à 20 000 sans indicateur** — conservé : un pipe de l'équipe compte quelques centaines d'entrées.
- **Excès** — retiré : `get_record`, `sorts` et le paramètre `sans_coordonnees`. Une réponse non JSON devient une `AttioError`.
