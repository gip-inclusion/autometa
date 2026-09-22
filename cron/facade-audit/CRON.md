---
title: Auditer la migration des tableaux de bord vers la façade
schedule: daily
timeout: 600
---

Mesure la migration vers `lib.dashboard_api` : combien de tableaux de bord cronnés importent encore
des modules internes du dépôt. `lib.dashboard_api` est né après eux — un TDB antérieur viole la
façade par construction, et sa migration est un chantier, pas un incident.

L'audit vivait dans `run_all()`, avant tout filtrage de batch : il téléchargeait le `cron.py` de
chaque TDB cronné sur S3 et postait la liste complète dans Slack **à chaque passe**, soit deux fois
par jour puisque `cron.json` planifie `--batch default` et `--batch xl` à la même heure. Ici, l'audit
tourne une fois par jour et n'alerte que quand l'ensemble des non conformes change : un canal où le
même pavé revient tous les jours cesse d'être lu, et ce sont les échecs RPE et runner qui s'y noient.

L'ensemble précédent est persisté dans `dashboard_storage.facade_audit_state`. Pendant l'exécution
d'un cron de TDB, `run_all()` garde une simple trace de journal sur le `cron.py` déjà téléchargé.
