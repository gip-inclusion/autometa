---
name: rediger_ticket
description: Rédiger un ticket du Backlog unifié à partir de notes, d'un vocal transcrit, d'un fil Slack ou d'un lien Figma ; le montrer avec l'équipe, le statut et l'épic recommandés ; le créer dans Notion seulement après l'accord explicite de l'auteur. (project)
---

# Rédiger un ticket du Backlog unifié

À utiliser quand quelqu'un demande un ticket, une carte ou une entrée de backlog à partir de ce qu'il colle.

Règle d'or : **tu n'inventes jamais de solution**. Tout ce que le ticket dit vient de l'entrée ou de la maquette. Ce que l'entrée laisse ouvert devient une question.

## Déroulé

1. **Maquette** : pour chaque lien Figma, `.venv/bin/python skills/rediger_ticket/scripts/maquette.py "<lien>"`, puis regarde chaque image citée avec l'outil Read. Suis `skills/rediger_ticket/maquette.md`.
2. **Contexte** : `.venv/bin/python skills/rediger_ticket/scripts/contexte.py` (équipes actives, épics actifs, tickets récents).
3. **Rédaction** : trie l'entrée, rédige, relis avec la liste finale. Exemples : `skills/rediger_ticket/exemples.md`.
4. **Doublons** : `.venv/bin/python skills/rediger_ticket/scripts/doublons.py "<titre>"`.
5. **Auteur** : `.venv/bin/python skills/rediger_ticket/scripts/auteur.py --equipe "<équipe recommandée>"`. Si ses rôles sont inconnus, demande-lui son rôle (PM, design, dev ou data, autre) et mets le champ correspondant dans le brouillon (`champ_auteur`). Correspondance : PM de l'équipe destinataire → `POM` ; PM d'une autre équipe → `Contributeurs` ; design → `UX` ; dev ou data → `Développeurs` ; tout autre rôle → `Contributeurs`. Sans compte Notion, dis-lui que le ticket sera créé sans auteur inscrit.
6. **Proposition** (format plus bas). Attends un accord explicite (« go », « crée-le », « ok »). Applique les corrections demandées et remontre si elles sont importantes.
7. **Création** : écris le brouillon avec Bash, dans le dossier de la conversation : `mkdir -p /tmp/rediger_ticket/${AUTOMETA_CONVERSATION_ID:-local} && cat > /tmp/rediger_ticket/${AUTOMETA_CONVERSATION_ID:-local}/brouillon.json <<'EOF'` … `EOF`. Lance `.venv/bin/python skills/rediger_ticket/scripts/creer.py` (vérification, rien n'est créé), puis `.venv/bin/python skills/rediger_ticket/scripts/creer.py --go`. Donne le lien du ticket. Le brouillon est supprimé après la création : pour un autre ticket, écris-en un nouveau. Une correction après la création se fait dans Notion, par le lien donné : ne relance jamais `--go` pour corriger.

Si un script répond « Refusé » ou « Notion répond … », corrige et relance la vérification. Sauf « Un ticket au même titre vient d'être créé » : donne ce lien à l'auteur et ne relance pas, même sous un autre titre. Après « Notion ne répond pas » pendant `--go`, vérifie si le ticket existe (`.venv/bin/python skills/rediger_ticket/scripts/doublons.py "<titre>"`, ou dans Notion) avant de relancer.

Tu ne poses jamais `Priorité`, `Période` ni `Estimation`. Tu peux recommander `𝗗𝗘𝗩 Prêt à développer` ; l'auteur choisit.

## 1. Trier l'entrée

| Ce que c'est | Où ça va |
|---|---|
| Besoin, problème, origine (support, réglementation, partenaire, données) | paragraphe d'ouverture |
| Règle, comportement, cas limite, texte exact, donnée affichée | « Attendu » ; textes recopiés mot pour mot, avec le vocabulaire de l'auteur |
| Décision de l'auteur ou du PM, même quand elle nomme un outil ou un composant | « Attendu », comme une contrainte |
| Livrable technique demandé sur le ton de l'exigence (« stocker l'opt-out par utilisateur », « une table dédiée ») | « Attendu » : c'est ce que le ticket livre |
| Contrainte externe : format imposé par un partenaire, paramètre d'URL fixé par un autre produit, délai légal | « Attendu », comme une contrainte |
| Discussion d'implémentation : idée d'un dev, diagnostic de l'auteur sur le code, idée sur le ton du « on pourrait », option renvoyée à plus tard | « Pistes techniques évoquées », attribuée par rôle, telle qu'elle a été dite, sans la durcir ni la compléter |
| Option discutée puis écartée | « Pistes techniques évoquées », avec « (écartée : motif) » si le motif est donné |
| Solution proposée par un usager ou le terrain | elle exprime le besoin : cite-la comme proposition du terrain, sans la présenter comme décidée |
| Réponse floue (« a priori », « genre ça ») | pas une décision : « À trancher » ou « (à confirmer) » |
| Hypothèse à vérifier | ouverture ou « Attendu » : « hypothèse : … » |
| Suite prévue dans un autre ticket | « Attendu » : « Hors périmètre (prévu ensuite) : … » |
| Dépendance bloquante | première puce d'« Attendu » : « Prérequis : … » |
| Valeur en fourchette (« 1 mois mini, 2 ce serait le luxe ») | « À trancher », avec la fourchette |
| Question réglée plus loin dans l'entrée | la réponse, dans « Attendu » |
| Aparté, impression isolée, anecdote, autre sujet | nulle part |

Ne calcule aucun chiffre que l'entrée ne donne pas. Vérifie que chaque question posée dans l'entrée a reçu une réponse explicite ; sinon, « À trancher ». Recopie les URL en entier. Reconstitue les noms déformés par la dictée quand c'est évident (`updated at` → `updated_at`), sinon signale le doute.

## 2. Forme du ticket

```
# <Titre>

:autometa: <Paragraphe d'ouverture>

## Périmètre
- Utilisateurs : …
- Écrans / parcours : …

## Attendu
- …
- Maquette : <lien Figma>

## À trancher
- … (qui tranche)

## Pistes techniques évoquées
- …

## Sources
- …
```

- **Titre** : un verbe à l'infinitif et son objet ; court, actif, explicite, 80 caractères au plus ; des mots que comprend quelqu'un qui n'a pas suivi la conversation. Un emoji est permis. Pas de « ETQ », pas de « URGENT ».
- **Ouverture** : directement sous le titre, sans en-tête, commence par `:autometa:` (le responsable le retire après relecture). 2 ou 3 phrases, 60 mots au plus : qui est concerné, quel problème, d'où il vient, ce qu'on veut obtenir.
- **Attendu** : des puces courtes, une idée par puce. Plusieurs blocs (variantes A et B, vue pro et vue candidat) : un intitulé en gras (`**Version A**`) puis ses puces, sans puces imbriquées. Si la solution reste à concevoir : « Solution à concevoir par l'UX », puis ce qui doit être vrai à la fin. Un critère de recette déduit par toi est marqué « (proposé) ».
- **À trancher** : les inconnues qui changent le travail, formulées pour qu'on y réponde, avec qui tranche. Zéro question est une bonne réponse.
- **Pistes techniques évoquées** et **Sources** : seulement si l'entrée en contient.
- **Longueur** : la prose de l'ouverture et des puces d'« Attendu » tient en 150 mots ; un changement de texte, en 60. Les textes recopiés, les livrables, les critères de recette, les pistes et les sources ne comptent pas. Ne coupe jamais un texte exact ni un livrable.
- **Données personnelles** : aucun nom de personne, de structure partenaire, d'e-mail ; les membres de l'équipe sont désignés par leur rôle. Rappelle-toi que les conversations d'autometa sont lisibles par tous.

## 3. Équipe, épic, doublons

- **Équipe** : celle dont le produit et l'écran sont concernés, d'après le contexte. L'équipe de l'auteur est un indice. Quand un membre d'une équipe demande quelque chose sur le produit d'une autre équipe : propose les deux et demande laquelle (ou les deux). Un demandeur du support, du déploiement, de la sécurité ou de la direction n'est pas une équipe destinataire.
- **Épic** : propose l'épic actif de l'équipe qui correspond clairement ; sinon, aucun.
- **Doublons** : parmi les candidats du script, ne retiens que ceux qui traitent vraiment du même sujet (deux au plus) ; propose alors de compléter le ticket existant plutôt que d'en créer un. Aucun candidat convaincant : n'en parle pas.

## 4. Statut recommandé

Lis ce qui existe, pas l'urgence. Prends la première ligne vraie :

| # | L'entrée montre… | Statut |
|---|---|---|
| 1 | un sujet volontairement mis de côté | `stand-by` |
| 2 | une idée sans engagement, ni règle ni comportement attendu (« pas urgent » seul ne suffit pas) | `Bac à sable 🏝️` |
| 3 | la règle centrale est inconnue (métier, réglementaire, partenaire), ou une analyse doit précéder la conception | `Métier` |
| 4 | le besoin est voulu, mais plusieurs options restent ouvertes ou le périmètre est à découper | `Cadrage` |
| 5 | il faut concevoir un écran et aucune maquette n'existe | `𝗨𝗫 À faire` |
| 6 | une maquette est en cours, ou ne couvre qu'une partie | `𝗨𝗫/𝗗𝗘𝗩 Conception` |
| 7 | une maquette du changement existe et rien ne dit qu'elle est validée | `𝗨𝗫 À valider` |
| 8 | tout est donné : règle, textes, maquette validée ou inutile | `𝗗𝗘𝗩 Prêt à développer` |

Un point périphérique ouvert (un seuil, un libellé, un cas rare) ne fait pas changer de ligne. Un lien Figma qui n'est pas une maquette du changement (documentation, vue d'ensemble) ne compte pas. Si tu ignores si la maquette est validée, choisis quand même et demande confirmation.

## 5. Proposition dans le chat

```
<le ticket, en Markdown>

---
**Équipe** : <équipe> (ou <autre>) · **Statut** : <statut> · **Type** : <type> · **Épic** : <épic ou aucun> · **Vous** : dans <champ>
<au plus 3 questions : équipe entre deux, maquette validée ?, ticket proche à compléter, lien annoncé mais absent>
Je crée le ticket ? Vous pouvez changer l'équipe, le statut ou le texte.
```

Pose les questions en texte (pas d'outil de question). Ne répète pas une question d'« À trancher ».

## 6. Brouillon pour la création

`/tmp/rediger_ticket/${AUTOMETA_CONVERSATION_ID:-local}/brouillon.json` (écrit avec Bash) :

```json
{
  "titre": "<titre, sans #>",
  "corps": "<le ticket sans la ligne de titre, en commençant par :autometa:>",
  "equipes": ["<nom exact d'équipe du contexte>"],
  "statut": "<statut exact>",
  "types": ["Fonctionnalité|Bug|Sécurité|Technique|Tâche"],
  "epic": "<nom exact d'un épic actif de ces équipes, ou absent>",
  "figma": "<lien Figma ou absent>",
  "champ_auteur": "<POM|UX|Développeurs|Contributeurs, seulement si l'auteur a donné son rôle>"
}
```

Le script refuse, avant toute écriture : un corps de plus de 100 blocs, une ligne de 2 000 caractères ou plus (découpe les longs textes recopiés en paragraphes), un lien qui n'est pas en `http://` ou `https://`, un lien Figma illisible, une équipe ou un épic qui ne correspond pas à Notion. Corrige et relance la vérification.

## Liste de vérification finale

- [ ] Titre : un verbe à l'infinitif et son objet, sans jargon opaque.
- [ ] Ouverture directement sous le titre, commençant par `:autometa:`.
- [ ] Aucune solution de toi ; chaque discussion d'implémentation de l'entrée est dans « Pistes techniques évoquées », attribuée.
- [ ] Chaque texte exact, livrable, lien et question restée ouverte de l'entrée est dans le ticket.
- [ ] Aucun nom de personne, de structure, ni donnée d'exemple de maquette.
- [ ] Équipe, statut, type, épic et champ de l'auteur justifiés ; 3 questions au plus.
