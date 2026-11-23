---
name: campagne_email
description: À utiliser pour créer, rédiger ou optimiser une campagne ou une séquence email (Brevo ou La Growth Machine). Pas pour en mesurer les résultats.
---

# Campagne email de La plateforme de l'inclusion

## Quand utiliser cette skill

Un bizdev demande de créer, de rédiger ou d'optimiser une campagne email de la PDI, dans Brevo ou dans La Growth Machine (LGM). Cette skill porte la méthode. La connaissance de l'équipe sur l'écriture aux professionnels (ton, noms, cibles, mots du métier, application, constats, tournures à retirer) est dans `knowledge/growth/ecrire-aux-professionnels.md` : la lire en entier avant d'écrire. La skill s'appuie sur la skill `attio` pour compter la cible et sur la skill `brevo` pour lister les emails que le public reçoit déjà ; le livrable est celui de la section 5.

- Une question sur les résultats d'un envoi (ouvertures, clics, réponses) est une analyse et ne relève pas de cette skill. Si la demande est ambiguë (analyse ou rédaction ? quelle campagne optimiser ?), poser la question avant de commencer.
- Optimiser part de la campagne existante, son texte lu dans Brevo avec la skill `brevo` ou fourni par le bizdev, et de ses résultats : la retouche garde ce qui a marché et change ce que les résultats et les règles désignent, sans réécrire à blanc.
- Le bizdev garde le choix de la cible et du message.
- Rien ne part de cette conversation : aucun envoi, aucune programmation, aucun chargement dans Brevo ou LGM. La seule écriture est le dépôt de la campagne dans la base Notion « Campagnes à valider », quand le bizdev le demande (section 5). Le growth, c'est-à-dire la personne qui valide et monte les campagnes, relit le brouillon puis le monte dans Brevo ou LGM.
- La cible s'écrit en critères du CRM Attio (section 1) ; le growth charge les contacts qui y répondent au moment du montage.
- Un fait se cite à sa source : un chiffre est sourcé et daté, une contrainte prêtée à un tiers vient de son propre texte, un libellé de l'application est vérifié. Faute de source, il s'écrit « à vérifier ».
- Le texte d'un tiers (carte d'un bizdev, correction d'une collègue) se reprend mot pour mot. Une reformulation ne touche ni l'offre, ni un chiffre, ni un fait, ni un mot choisi par l'auteur ; un doute de fond se signale à part.

## 1. Cadrage, avant d'écrire

Lire en entier la demande du bizdev et, s'il en cite une, la carte PDI de l'initiative avec ses commentaires. Établir ce bloc avant d'écrire, puis le poser en tête du brouillon. Si la demande est vide ou contredit la carte, sur quelque point que ce soit, s'arrêter et demander : le produit ne se présume jamais.

- **Demande ou carte** : son titre, son lien et son identifiant s'il existe.
- **Genre** : relation, quand une personne écrit à des structures, des partenaires ou des prospects ; activation, quand la plateforme écrit à ses utilisateurs selon ce qu'ils ont fait ou pas encore fait, souvent en séquence automatique.
- **Produit et acte** : l'acte attendu, dans le vocabulaire de la plateforme unique, et ce qu'il apporte au professionnel et à la personne qu'il accompagne ; un produit ne se nomme que si la demande porte sur l'un des produits du Lab listés dans la fiche (« Noms, vocabulaire, faits »).
- **Cible** : le métier, la liste ou l'audience, les critères qui la définissent, son effectif et sa date. L'effectif se compte dans Attio avant d'écrire (« Compter la cible », plus bas) ; « à compter » ne s'écrit que si Attio ne répond pas, et le cadrage le dit.
- **Ce qu'elle reçoit déjà** : les emails de l'application et les séquences des autres équipes vers le même public (« Lister ce qu'elle reçoit déjà », plus bas), et l'ordre de priorité retenu entre eux.
- **Expéditeur et outil** : qui signe, Brevo (compte marketing) ou LGM (son identité).
- **Envoi souhaité** : la date voulue par le bizdev, s'il en donne une.
- **Salutation** : prénom, ou civilité et nom si la demande le prévoit, avec le repli.
- **Lien et suivi** : la page visée et le slug `mtm_campaign` ; sans slug, en proposer un dans le cadrage et le reprendre dans les questions finales.
- **Qui valide** : la personne qui suit la cible pour l'acte proposé (la CSM de ce public, ou la bizdev du territoire), la responsable du contenu pour le texte d'une activation, la personne qui signe pour une relation.

Une contradiction entre la demande et la carte arrête toujours l'écriture. Parmi les points qui manquent, seules la cible et l'acte bloquent : s'ils manquent, s'arrêter et demander. Les autres points ouverts (priorité avec les autres envois, lien, validation, choix de fond) ne réduisent pas le livrable : la séquence demandée s'écrit en entier, chaque point reçoit l'hypothèse la plus probable, écrite dans le cadrage, et la question qui reste se pose à la fin. Un fait qui manque (URL d'un article, date, source) se cherche d'abord dans la demande et sur le web, et ne devient une question que si la recherche échoue. Les questions finales sont cinq au plus : pour chacune, le brouillon applique déjà l'option la plus proche du texte de l'auteur et dit laquelle.

Une action se conçoit depuis le travail du professionnel et l'intérêt de la personne qu'il accompagne. Un indicateur interne mesure son effet, il ne choisit ni la cible ni l'acte.

**Compter la cible.** La cible se compte dans le CRM Attio avec la skill `attio`, qui documente les objets, les attributs et leurs valeurs. Le critère métier reste ici : une cible se choisit sur son métier (accompagne-t-elle des personnes qui ont un frein ?), jamais sur sa présence actuelle sur la plateforme, et une prospection écarte les contacts qui utilisent déjà le produit proposé.

- Traduire la demande en filtres (types de structure, départements, fonctions visées, statut), après avoir lu les valeurs possibles de chaque attribut, les écrire dans le cadrage, puis donner l'effectif : nombre de structures et nombre de contacts, répartis par fonction ou par département.
- Pour choisir la cible, les totaux et les répartitions suffisent. Une liste nominative ne sert qu'à relire la cible avec le bizdev, par exemple pour vérifier qu'un réseau y est. Aucun de ses noms, adresses ou structures ne se recopie dans les emails ni dans le livrable.
- Les désinscrits ne se lisent ni dans Attio ni par la skill `brevo` : le growth les retire au montage, et le cadrage le rappelle.

**Lister ce qu'elle reçoit déjà.** Avant de concevoir un envoi vers un public, les emails des produits et les campagnes de l'équipe se listent, pour qu'une personne ne reçoive pas deux messages sur le même sujet. La skill `brevo` lit les modèles et leurs volumes d'envoi sur les comptes des produits (`emplois`, `dora`) et les campagnes récentes de l'équipe sur le compte `marketing`. Elle ne lit ni les listes ni les destinataires : elle ne dit pas si un modèle vise le même public. Le rapprochement se fait donc par sujet (nom et objet du modèle ou de la campagne) et par compte, et le cadrage le présente comme une hypothèse que le growth confirme. Le cadrage écrit « à vérifier » seulement si la skill `brevo` ne répond pas.

## 2. Format selon l'outil

Le growth monte la campagne. Le brouillon s'écrit pourtant au format de l'outil, pour qu'il se charge sans retouche.

**Brevo.**

- Toute campagne part du compte marketing.
- Le prénom est `FIRSTNAME`, sous condition : `{% if contact.FIRSTNAME %}Bonjour {{ contact.FIRSTNAME }},{% else %}Bonjour,{% endif %}`. `PRENOM` n'existe pas sur le compte. Toute autre variable doit exister sur le compte, et le brouillon liste celles qu'il emploie.
- Seule la condition de présence est éprouvée. Un singulier et un pluriel se traitent par deux listes, pas par une comparaison de nombre.
- La signature s'écrit dans le corps et reprend le nom d'expéditeur. `{{signature}}` n'existe pas dans Brevo.
- Chaque email porte en pied la raison de réception propre à la liste, `{{ unsubscribe }}` et `{{ revoke_open_pixel_tracking }}`.
- L'expéditeur est la personne qui signe, jamais un nom générique : un envoi signé « L'équipe Mon Récap » a été très peu ouvert. Au-delà de 2 000 destinataires, le growth utilise un expéditeur d'équipe, parce que les réponses automatiques arrivent dans la boîte de l'expéditeur.
- En réactivation et en onboarding, le bouton mène à l'acte (« Voir la candidature à traiter ») : « Quinze minutes avec votre équipe ? » a été beaucoup moins cliqué que les boutons d'acte de la même série.
- L'objet fait 50 caractères au plus et nomme la situation du destinataire ; le préheader le complète. Sur une liste de quelques centaines de contacts, un seul objet par email.
- Jamais le même jour qu'un gros envoi vers une liste qui recoupe : Brevo écarte alors des destinataires en silence.

**LGM.**

- La salutation se calcule à l'import (« Bonjour Prénom, », ou « Bonjour, » pour une adresse générique) et s'écrit `<var name="customAttribute1" default="Bonjour,"/>`. Jamais `firstname` sans repli.
- LGM ajoute la signature de l'identité, qui contient la désinscription. Le corps ne porte ni `<signature/>`, ni `{{signature}}`, ni nom écrit, ni ligne de désinscription.
- Les relances n'ont pas d'objet : elles partent dans le même fil.
- En prospection, l'appel à l'action est une question fermée ou un échange proposé au conditionnel, avec sa durée. Aucun message ne parle d'« accord » ni ne présente un intérêt exprimé plus tôt comme un engagement, et aucune note d'invitation LinkedIn ne porte l'offre.
- Une campagne par canal. L'identité, les délais, le nom des étapes et le lancement se règlent dans l'app, par le growth. Le nom d'étape « GOOGLE message - step N » n'entre jamais dans un texte.

**Liens, dans les deux outils.** Le lien se pose sur la première mention du service et vise une page profonde, jamais la racine de `plateforme.inclusion.gouv.fr`, qui perdait les paramètres. Il porte l'URL de suivi (`mtm_campaign`, `mtm_source`, `mtm_medium`) et `mtm_content=e1`, puis e2 et e3. Aucun lien provisoire ne reste, et une date est identique dans l'objet, le corps et le lien.

## 3. Exemples

Les textes sont cités tels qu'ils sont partis, avec leurs variables d'origine, parfois en extrait, liens abrégés. Un exemple se reprend pour sa mécanique, jamais phrase à phrase, et la ligne « À reprendre aujourd'hui » dit ce que les règles de cette skill et de la fiche y changent.

### Relation, LGM : délégataires du RSA transmis par les Conseils départementaux (24/09)

Ce qui marche : la source du contact dès la première phrase, des services décrits par leur usage, un seul lien.

```
Objet : Pour vos accompagnements RSA

{{customAttribute2}}

Le Conseil départemental {{customAttribute1}} nous a transmis les coordonnées de votre structure pour vous présenter les services de la Plateforme de l’inclusion utiles à l’accompagnement des allocataires du RSA.

Vous pouvez y rechercher une solution de mobilité ou une formation, orienter une personne vers un emploi en insertion et retrouver les professionnels qui l’accompagnent déjà.

Ces services publics sont gratuits et désormais réunis dans un même espace. Vous pouvez les découvrir et créer votre compte ici :

[Découvrir la Plateforme de l’inclusion](lien)

Si vous souhaitez partir d’une situation rencontrée par votre équipe, nous pourrions prendre 15 minutes pour en discuter.

Bonne journée,
```

À reprendre aujourd'hui : « La plateforme de l'inclusion » dans sa casse ; « créer votre compte » sort ; le lien vise une page profonde avec `mtm_` ; la salutation suit la section 2 (`<var name="customAttribute1" default="Bonjour,"/>`), et une autre variable, comme le département, prend un autre attribut (`customAttribute2`) dans la même syntaxe.

### Relation, LGM : unions départementales de CCAS (20/07)

Ce qui marche : le rôle demandé au relais en trois options précises, la charge prise entièrement par l'équipe, une relance qui propose une présentation pendant une réunion déjà prévue.

```
Objet : DORA et les CCAS {{customAttribute1}}

{{customAttribute2}}

Vous connaissez mieux que personne les CCAS {{customAttribute1}} : leurs équipes, leurs outils, ce qui leur manque pour orienter les personnes qu'ils accompagnent.

DORA, service public numérique de la Plateforme de l'inclusion, recense les solutions d'insertion de chaque territoire pour que les CCAS y orientent directement. Plusieurs UDCCAS l'ont déjà pris en main : les premiers déploiements sont engagés et de nouvelles sessions se programment.

Vous pouvez jouer un rôle simple : relayer l'information à vos adhérents, nous signaler les CCAS intéressés, ou nous ouvrir un temps de présentation. L'animation, la démonstration et l'accompagnement restent entièrement à notre charge.

Nous pourrions prendre 15 minutes pour en discuter ?
```

```
Relance 1 (sans objet)

{{customAttribute2}}

Beaucoup d'UDCCAS profitent d'un rendez-vous déjà au calendrier, journée départementale, groupe de travail ou réunion d'adhérents, pour y glisser une présentation de DORA.

De votre côté, il n'y a qu'un créneau à ouvrir. Nous arrivons avec la démonstration et les cas concrets, et nous restons ensuite en appui des CCAS qui veulent se lancer.

Y a-t-il une date dans vos prochaines semaines où cela pourrait se caler ?
```

À reprendre aujourd'hui : « La plateforme de l'inclusion » dans sa casse ; DORA ne se nomme plus, l'objet et le corps décrivent l'acte dans La plateforme de l'inclusion ; la dernière relance annonce la fin des relances et pose une dernière question utile. « Nous ouvrir un temps de présentation » et « il n'y a qu'un créneau à ouvrir » se disent sans image : présenter l'outil aux adhérents lors d'une réunion déjà prévue. Les variables suivent la même règle que l'exemple précédent : la salutation suit la section 2 (`<var name="customAttribute1" default="Bonjour,"/>`), et une autre variable, comme le département, prend un autre attribut (`customAttribute2`) dans la même syntaxe.

### Activation, Brevo : une échéance propre à la personne (07/09)

Ce qui marche : une échéance personnelle, la conséquence dite à plat, un bouton qui mène à la liste à traiter.

```
Expéditeur : [Prénom] de La plateforme de l'inclusion
Objet : Un profil qui va sortir de votre espace
Préheader : Reçue avant août, cette candidature attend toujours une réponse

Bonjour{% if contact.FIRSTNAME %} {{ contact.FIRSTNAME }}{% endif %} 👋

Une candidature reçue avant le 1er août attend encore une réponse sur votre espace. Elle en sort le {{ contact.PREMIERE_ECHEANCE }} : passé deux mois sans réponse, la plateforme la refuse à votre place, avec un message type au candidat.

Si le profil peut convenir à une prochaine ouverture de poste, le garder sous la main prend deux minutes : il vous suffit de passer la candidature en attente, avec un mot sur la suite. Le candidat et le prescripteur qui vous l'a adressée voient où ça en est.

Accepter ou décliner marche aussi. Une réponse, même négative, garde la confiance des prescripteurs qui vous envoient des candidats.

[Voir la candidature à traiter](lien avec mtm_)

[Prénom] de La plateforme de l'inclusion
```

À reprendre aujourd'hui : « le garder sous la main » et « il vous suffit de » sortent ; le lien vise une page profonde de `plateforme.inclusion.gouv.fr`, avec `mtm_` ; la salutation suit la section 2, avec sa virgule et sans emoji.

### Activation : un brouillon et sa correction par la responsable du contenu

Un extrait du brouillon :

```
Objet : Proposer une candidature en quelques minutes

Votre espace sur la plateforme de l'inclusion est ouvert depuis deux jours.

Depuis votre tableau de bord :
• chercher un emploi inclusif près de chez elle ;
• ouvrir le poste qui lui correspond et cliquer sur Postuler ;
• valider son éligibilité, puisque votre agence est habilitée ;
• suivre la réponse de l'employeur dans Demandes envoyées.
```

Le même passage corrigé :

```
Bienvenue sur La plateforme de l'inclusion !

Depuis votre tableau de bord :
• cherchez un emploi inclusif près de chez elle ;
• ouvrez le poste qui lui correspond et cliquez sur « Postuler » ;
• validez son éligibilité à l'IAE : en tant que prescripteur, vous êtes habilité à le faire ;
• suivez la réponse de l'employeur dans « Demandes envoyées ».

Besoin d'un pas-à-pas ? Tout est expliqué dans notre guide : [Proposer une candidature](article du centre d'aide)
```

Autres corrections de la même série :

| Brouillon | Correction |
|---|---|
| Objet « Pour la personne que vous venez de proposer », envoyé deux jours après la candidature | « Candidature envoyée : et en attendant ? » |
| « un autre problème à régler avant de reprendre un emploi » | « un frein à lever » |
| Bouton « Je trouve un service » | « Je cherche un service » |
| « En septembre, plus de 900 professionnels ont adressé une personne à un service d'insertion. » | « le mois dernier, plus de deux demandes sur trois ont été acceptées » |
| « Le service vous répond dans votre espace. » | « Vous êtes prévenu par email de sa réponse, que vous retrouvez aussi dans l'onglet « Demandes envoyées » sur votre espace. » |
| « Si la structure n'a pas encore répondu, ses coordonnées figurent sur sa fiche. » | « Pas encore de réponse ? Vous pouvez contacter la structure : ses coordonnées figurent dans le détail de la candidature. » |
| « Une fois ce frein levé, elle sera peut-être prête à reprendre un emploi. » | « Pas besoin d'attendre que tous ses freins soient levés pour penser à l'emploi. » |

## 4. Relecture avant de rendre

Relire chaque email en entier : l'objet et le préheader d'abord, seuls, puis le corps, de la salutation à la signature. Un contrôle vaut « oui » quand tout le brouillon le respecte, « non » dès qu'une ligne le viole. Chaque « non » se corrige avant de rendre.

1. **Cadrage.** L'en-tête est complet et conforme à la demande : même produit, même acte, même cible, même expéditeur. Le livrable est celui que la demande attend ; un point ouvert autre que la cible ou l'acte figure comme hypothèse dans le cadrage, sans réduire le livrable.
2. **Fond intact.** Le texte d'un tiers est repris mot pour mot, et quand le bizdev a écrit ses brouillons, chaque email part de son texte : une phrase retirée ou changée l'est pour un motif des « Tournures à retirer » de la fiche ou figure dans les questions ; l'offre, les chiffres et les faits de la demande n'ont pas changé ; rien de la conversation n'apparaît dans les emails.
3. **Faits.** Chaque chiffre a une source datée ; une fonctionnalité non livrée est dite engagée ; une date est identique dans l'objet, le corps et le lien ; aucun cas isolé ne sert de preuve.
4. **Noms.** La table « Noms, vocabulaire, faits » de la fiche est respectée : « La plateforme de l'inclusion » dans sa casse, aucun ancien produit, ni « compte » ni « annuaire », « orientation » jamais seule.
5. **Variables et salutation.** Les variables existent, la salutation a sa valeur de repli, et aucun nom ni aucune adresse de destinataire ne figure dans le brouillon : les variables résolues prennent des valeurs fictives.
6. **Canal.** Brevo : signature écrite identique à l'expéditeur, pied complet, aucun expéditeur générique sous 2 000 destinataires (section 2). LGM : relances sans objet, corps sans signature ni désinscription, aucun « accord » ni intérêt passé présenté comme un engagement. Nulle part un nom d'étape « step N ».
7. **Liens.** Un lien sur la première mention du service, vers une page profonde, avec le suivi `mtm_` ; aucun lien provisoire.
8. **Appel à l'action et structure.** Un seul par email, adapté au genre. Un angle nouveau à chaque relance ; en relation, une seule porte de sortie par séquence et une clôture qui annonce la fin des relances avec une dernière question, sans parler de la boîte du destinataire.
9. **Ton.** Selon le genre (fiche, « Ton, selon le genre »). Aucun tiret long et les mots du métier gardés, objet et préheader compris. Un « on » ou un motif des « Tournures à retirer » ne vaut « non » que s'il rend le texte sec, artificiel ou maladroit. Aucun paragraphe ne dépasse trois phrases, plusieurs faits passent en liste, chaque paragraphe passe les trois tests de la relecture de la forme (fiche), et la demande dit sans image qui fait quoi, devant qui et combien de temps.
10. **Connotation.** Les rôles sont épicènes, aucune formule n'associe l'insertion à une contrainte, aucune instance politique n'est nommée sans besoin, et aucun mot ne peut blesser la cible.

## 5. Livraison

Le livrable se donne dans la conversation, dans cet ordre :

1. Le cadrage de la section 1.
2. Les emails complets pour un cas représentatif de l'audience : salutation, paragraphes, liens, formule de fin et signature visibles. Les variables s'y résolvent avec des valeurs fictives (« [Prénom] », « [Département] », « [Structure] »), comme dans les exemples, jamais avec un vrai contact : ni dans la conversation, ni dans la page Notion.
3. Le gabarit technique ci-dessous, prêt à charger par le growth.
4. Le tableau des dix contrôles de la section 4, avec leur verdict.
5. Les questions de fond qui restent (offre, ciblage, choix de l'auteur), à part, cinq au plus, chacune avec l'option que le brouillon applique déjà.

```
# <nom de la campagne>
Demande ou carte PDI : <titre> (<lien>)
Genre : Relation | Activation · valide : <qui>
Produit et acte : La plateforme de l'inclusion · <acte>
Cible : <métier> · <liste ou audience> (<n> contacts au <date>, ou « à compter » si Attio ne répond pas)
Outil : Brevo, compte marketing | La Growth Machine
Expéditeur : <nom affiché>
Envoi souhaité : <date, si elle est connue>
Salutation : <prénom ou civilité et nom> · repli : Bonjour,
Suivi : mtm_campaign=<slug>&mtm_source=<équipe>&mtm_medium=<medium>&mtm_content=e1 (e2, e3 ensuite)
Pied (Brevo) : <raison de réception> · {{ unsubscribe }} · {{ revoke_open_pixel_tracking }}

## E1 · J0
Objet : …
Préheader (Brevo) : …

<salutation>

<paragraphes séparés par une ligne vide ; [texte](url) ; [Bouton : acte](url)>

<formule de fin>
<signature, Brevo seulement>

## E2 · J+5
Objet : …   (LGM : aucun, même fil)
```

La campagne est prête quand les dix contrôles valent « oui » et qu'aucune question ne bloque. L'agent montre alors le livrable et propose une relecture au bizdev : il corrige ce que le bizdev demande et remontre le livrable si les corrections sont importantes. Il dépose la campagne dans la base Notion « Campagnes à valider » seulement quand le bizdev le dit (« dépose-la », « c'est bon pour le growth »). Une exception : si la première demande du bizdev demandait explicitement le dépôt dans Notion, l'agent dépose directement une fois la campagne prête, puis propose la relecture.

Pour déposer :

1. Écrire la campagne avec Bash, dans le dossier de la conversation : `mkdir -p "/tmp/$AUTOMETA_CONVERSATION_ID" && cat > "/tmp/$AUTOMETA_CONVERSATION_ID/campagne.json" <<'EOF'` … `EOF`. Un objet JSON avec `campagne` (le nom), `outil` (`brevo` ou `lgm`), `genre` (`relation` ou `activation`), `cible` (les critères), `departements`, `structures` et `contacts` (des effectifs, jamais une liste nominative), `expediteur`, `carte_pdi` (le lien de la carte, s'il existe), `envoi_souhaite` (AAAA-MM-JJ, s'il est connu) et `corps` (le livrable ci-dessus, en markdown). Dans le corps, l'email s'écrit en paragraphes simples, sans citation ni bloc de code.
2. Lancer `python -m skills.campagne_email.scripts.deposit` : il montre la page qui serait écrite, et rien n'est écrit.
3. Lancer `python -m skills.campagne_email.scripts.deposit --go`. Le script pose le statut « À valider », les valeurs exactes des options de la base, la personne qui fait la demande et le lien de cette conversation quand il les connaît, et dit ce qu'il a laissé vide.

Après un dépôt, une correction se fait dans le même fichier, puis `--go` se relance : le script met à jour la même page, il n'en crée pas une seconde. Si le script répond « Refusé », corriger le fichier et relancer la vérification. Après « Notion ne répond pas » pendant `--go`, vérifier dans Notion si la page existe avant de relancer.

La réponse donne le lien de la page et rappelle en une phrase que le growth valide avant tout chargement, et que rien ne part sans lui.
