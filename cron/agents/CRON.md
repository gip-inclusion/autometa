---
title: Faire tourner les agents
schedule: daily
timeout: 3600
batch: maintenance
---

Pour chaque agent actif (skill `agents`) : livre ses runs terminés depuis le passage précédent,
puis, si sa cadence tombe aujourd'hui, fait tourner ses préparations dans l'ordre et lance son
run. Un agent est un déclenchement périodique, pas un processus allumé : le worker de chaque run
est un conteneur jetable. Un agent en échec n'empêche pas les autres ; la tâche sort en échec
et nomme les agents concernés.
