Invariants de sécurité — vrais pour toute demande, donc jamais recopiés dans une Definition of Done.

**Le dépôt est public** et le produit manipule des données sur des demandeurs d'emploi. Aucune donnée
personnelle ne doit être committée : ni extrait de conversation réelle, ni export de requête, ni
capture d'écran d'une page contenant des données de production. Un historique git public ne s'efface
pas. Pour anonymiser du texte réel avant de le manipuler, utiliser `lib/pii.py`.

**Les sorties de modèle sont des entrées non fiables.** Tout texte produit par un agent ou un LLM est
assaini avant rendu (`web/deps.py:markdown_filter`), jamais interpolé dans du SQL, jamais exécuté.
L'injection de prompt est un vecteur d'attaque, pas une curiosité.

**Toute communication externe passe par TLS**, avec un timeout explicite (`S113`). Les secrets vivent
dans des variables d'environnement lues par `web/config.py`, jamais dans le code ni dans un fichier
committé.

**Les dépendances sont épinglées** (`uv.lock`) et auditées par le job nightly `Dependencies`. Le
vendoring manuel demande une justification écrite.

**Moindre privilège sur les routes** : une route FastAPI naît sans protection, l'autorisation s'écrit
route par route. `scripts/check_route_auth.py` refuse toute route neuve absente de la baseline gelée
dans `gates.toml`, et refuse aussi une entrée devenue inutile — la baseline se résorbe, elle ne
s'étend pas.
