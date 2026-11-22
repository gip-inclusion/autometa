---
name: campagne_email
description: Rédiger une campagne ou une séquence email de la Plateforme de l'inclusion (Brevo ou La Growth Machine) à partir de la demande d'un bizdev, jusqu'au brouillon prêt à valider. À utiliser dès qu'une demande parle de campagne, de séquence, de relance ou d'email à envoyer à des professionnels.
---

# Campagne email de la Plateforme de l'inclusion

Version du 17/11/2026.

## Quand utiliser cette skill

Un bizdev demande une campagne email de la PDI, dans Brevo ou dans La Growth Machine (LGM). Cette skill contient toute la méthode de rédaction. Elle s'appuie sur la skill `attio` pour compter la cible, sur la skill `brevo` pour lister les emails que le public reçoit déjà, et sur la skill `notion` pour déposer la campagne prête. La demande est une rédaction de campagne, pas une analyse de données : le livrable est celui de la section 12.

- Le bizdev garde le choix de la cible et du message.
- Rien ne part de cette conversation : aucun envoi, aucune programmation, aucun chargement dans Brevo ou LGM. La seule écriture est le dépôt de la campagne prête dans la base Notion « Campagnes à valider » (section 12). Le growth, c'est-à-dire la personne qui valide et monte les campagnes, relit le brouillon puis le monte dans Brevo ou LGM.
- La cible s'écrit en critères du CRM Attio (section 5) ; le growth charge les contacts qui y répondent au moment du montage.
- Un fait se cite à sa source : un chiffre est sourcé et daté, une contrainte prêtée à un tiers vient de son propre texte, un libellé de l'application est vérifié. Faute de source, il s'écrit « à vérifier ».
- Le texte d'un tiers (carte d'un bizdev, correction d'une collègue) se reprend mot pour mot. Une reformulation ne touche ni l'offre, ni un chiffre, ni un fait, ni un mot choisi par l'auteur ; un doute de fond se signale à part.

## 1. Cadrage, avant d'écrire

Lire en entier la demande du bizdev et, s'il en cite une, la carte PDI de l'initiative avec ses commentaires. Établir ce bloc avant d'écrire, puis le poser en tête du brouillon. Si la demande est vide ou contredit la carte, sur quelque point que ce soit, s'arrêter et demander : le produit ne se présume jamais.

- **Demande ou carte** : son titre, et son identifiant s'il existe.
- **Genre** : relation, quand une personne écrit à des structures, des partenaires ou des prospects ; activation, quand la plateforme écrit à ses utilisateurs selon ce qu'ils ont fait ou pas encore fait, souvent en séquence automatique.
- **Produit et acte** : l'acte attendu, dans le vocabulaire de la plateforme unique, et ce qu'il apporte au professionnel et à la personne qu'il accompagne ; un produit ne se nomme que si la demande porte sur un produit du Lab.
- **Cible** : le métier, la liste ou l'audience, les critères qui la définissent, son effectif et sa date. L'effectif se compte dans Attio avec la skill `attio` avant d'écrire (section 5) ; « à compter » ne s'écrit que si Attio ne répond pas, et le cadrage le dit.
- **Ce qu'elle reçoit déjà** : les emails de l'application et les séquences des autres équipes vers le même public (section 7), et l'ordre de priorité retenu entre eux.
- **Expéditeur et outil** : qui signe, Brevo (compte marketing) ou LGM (son identité).
- **Salutation** : prénom, ou civilité et nom si la demande le prévoit, avec le repli.
- **Lien et suivi** : la page visée et le slug `mtm_campaign` ; sans slug, en proposer un dans le cadrage et le reprendre dans les questions finales.
- **Qui valide** : la personne qui suit la cible pour l'acte proposé (la CSM de ce public, ou la bizdev du territoire), la responsable du contenu pour le texte d'une activation, la personne qui signe pour une relation.

Une contradiction entre la demande et la carte arrête toujours l'écriture. Parmi les points qui manquent, seules la cible et l'acte bloquent : s'ils manquent, s'arrêter et demander. Les autres points ouverts (priorité avec les autres envois, lien, validation, choix de fond) ne réduisent pas le livrable : la séquence demandée s'écrit en entier, chaque point reçoit l'hypothèse la plus probable, écrite dans le cadrage, et la question qui reste se pose à la fin. Un fait qui manque (URL d'un article, date, source) se cherche d'abord dans la demande et sur le web, et ne devient une question que si la recherche échoue. Les questions finales sont cinq au plus : pour chacune, le brouillon applique déjà l'option la plus proche du texte de l'auteur et dit laquelle.

Une action se conçoit depuis le travail du professionnel et l'intérêt de la personne qu'il accompagne. Un indicateur interne mesure son effet, il ne choisit ni la cible ni l'acte.

## 2. Ton, selon le genre

La PDI est un service public qui écrit comme une personne, au vouvoiement, chaleureux sans familiarité. Les repères de cette section viennent des retouches du growth et de l'équipe et décrivent ce ton : une tournure qu'ils écartent d'habitude peut rester dans un email quand elle le sert, et la relecture en juge au cas par cas. Le tiret long ne passe jamais. Les cas connus :

- « nous » est la voix de l'institution, et un « on » naturel peut rester dans une activation (« on vous propose une session de prise en main ») ;
- « il ne reste qu'à » passe quand le lecteur a déjà fait l'essentiel (« il ne reste qu'à lui envoyer une demande depuis sa fiche »), alors qu'une demande présentée comme dérisoire (« un oui ou un non me suffit ») se reformule ;
- une liste de besoins concrets (« logement, santé, mobilité… ») informe, y compris dans un objet, tandis que trois mots posés pour le rythme se retirent ;
- un paragraphe porte une idée, en deux ou trois phrases complètes et 40 mots au plus, et une phrase seule peut accueillir ou rappeler l'acte. Quand un email apporte plusieurs faits ou chiffres, une phrase les annonce (« Quelques chiffres : ») et ils suivent en liste, un fait par ligne, marquée par « • ». Une ligne vide sépare chaque paragraphe.

Les mots du métier (« lever un frein », « bénéficiaire », « structure d'insertion ») sont la langue courante des destinataires et se gardent (section 6). L'argument part d'un problème du destinataire ou de la personne qu'il accompagne, jamais d'un indicateur à nous, et l'email n'explique pas ce que le destinataire sait déjà : son métier, ou l'outil s'il s'en sert depuis longtemps.

**Relation.** La chaleur attendue tient à cinq gestes, tirés des retouches faites sur les campagnes de prospection et de partenariat :

1. **Une salutation jamais vide** : le prénom, comme « Bonjour Prénom, », sinon « Bonjour, » ou « Bonjour Madame, Monsieur, ».
2. **Une première phrase qui situe ou remercie** avant toute demande : la source du contact (« Le Conseil départemental … nous a transmis les coordonnées de votre structure »), le métier du destinataire ou un merci réel.
3. **L'offre présentée comme une bonne nouvelle** (« Nous avons le plaisir de vous proposer ») et **la demande au conditionnel** (« pourriez-vous », « souhaitez-vous », « nous pourrions prendre 15 minutes pour en discuter »).
4. **Une formule de fin** avant la signature : « Belle journée, », « Bien cordialement, ».
5. **Une porte ouverte** si la personne qui signe lit les réponses : une invitation à répondre, puis une clôture qui annonce la fin des relances et pose une dernière question utile. La porte de sortie (« si le sujet n'est pas le vôtre ») ne figure qu'une fois par séquence.

Un texte court retire une idée, jamais l'un de ces gestes. À froid dans LGM, viser environ 70 mots au premier email, 50 en relance, 25 en clôture et moins de 60 sur LinkedIn. Quand le bizdev a écrit ses propres brouillons, leur longueur et leur structure prévalent sur ces cibles : la retouche ne comprime jamais le texte en un seul paragraphe pour gagner des mots. Une campagne Brevo de masse est un message institutionnel signé d'un prénom, écrit avec « nous » ; une séquence LGM, envoyée à une personne, emploie « je » et « nous ». Le registre suit la personne qui signe et se prend dans ses emails déjà envoyés : sa formule de fin, son usage des emojis et ce qu'elle propose d'habitude (présentation de 30 minutes, lien d'agenda, flyer, lien d'inscription). Demander au bizdev un de ses emails envoyés quand il signe.

**Activation.** La plateforme parle à quelqu'un qui l'utilise et l'aide à faire un geste précis. Le ton accueille, situe le lecteur et lui dit précisément quoi faire et où. Les corrections de la responsable du contenu reviennent sur ces points :

- L'email se comprend des jours après l'acte qui le déclenche : l'objet et la première phrase accueillent (« Bienvenue sur La plateforme de l'inclusion ! ») ou rappellent l'acte et la situation du lecteur (« Candidature envoyée : et en attendant ? », « Il y a une semaine, vous avez proposé une candidature… »).
- Il part de ce que la personne a déjà fait et propose le geste suivant, un seul, avec ce qu'il apporte au professionnel et à la personne qu'il accompagne. Il dit ce qu'une étape permet plutôt que ce qui manque, et n'ouvre pas sur un échec comme un refus. Une condition qui changerait le geste fait un second email.
- Les étapes sont à l'impératif, avec les libellés exacts des écrans entre guillemets (l'onglet « Demandes envoyées »), et l'email dit où la réponse arrivera. Une condition se pose souvent en question courte (« Pas encore de réponse ? Vous pouvez contacter la structure. »).
- Le bouton nomme ce que la personne va faire (« Je cherche un service », pas « Je trouve un service »), et l'article du centre d'aide suit quand il existe et qu'il est à jour (« Besoin d'un pas-à-pas ? »).
- Une séquence qui tourne des mois ne porte aucun chiffre daté : une proportion stable et sourcée le remplace (« le mois dernier, plus de deux demandes sur trois ont été acceptées »).

Dans les deux genres, la phrase qui contient une variable ferme son paragraphe. Une séquence compte trois emails au plus (J0, J+5, J+10), sauf décision écrite, chaque relance apporte un angle nouveau, et chaque campagne a ses propres phrases.

## 3. Format selon l'outil

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

## 4. Noms, vocabulaire, faits

Vers une cible, l'offre se présente sous le nom de la plateforme et par l'acte. Ces noms se cherchent aussi dans les colonnes de personnalisation.

| Nom | S'écrit | Ne s'écrit pas |
|---|---|---|
| La plateforme de l'inclusion | L majuscule même en milieu de phrase (« depuis La plateforme de l'inclusion »), p minuscule, partout, expéditeur et signature compris ; en entier la première fois, objet compris, puis « la plateforme » | la Plateforme de l'Inclusion, la plateforme de l'inclusion, application unifiée |
| L'acte | orienter une personne vers un service d'insertion, rechercher un service, répondre à une candidature ; « votre espace sur La plateforme de l'inclusion » | orientation sans complément, compte, annuaire, migration, bascule, fusion |
| Anciens produits | jamais vers une cible : nommer l'acte | Les Emplois (de l'inclusion), GPS, Pilotage, data·inclusion, Communauté |
| DORA | seulement dans les messages sur l'orientation à partir du 16/11/2026, adressés à qui orientait depuis DORA, avec le narratif (« DORA reste l'outil de recherche ») | « DORA ferme », « rien ne change » |
| Produits du Lab, si la demande porte sur eux | Mon Récap ; Les traiteurs engagés ; Le marché de l'inclusion ; rdv-insertion | Mon Recap ; Les Traiteurs engagés ; RDV-Insertion |
| Partenaires et programmes | France Travail ; le Conseil départemental, le Département ; CCAS, UDCCAS ; DIHAL ; PASS IAE ; Jeudi de l'inclusion | Pôle emploi |

- Les produits ne se nomment plus devant une cible, DORA compris : l'email parle de l'acte et de La plateforme de l'inclusion. Quand une demande, un brouillon du bizdev, un article ou une objection citée nomme un produit, l'email le reformule sans le nommer (« les offres DORA ne sont pas fiables » devient « les services référencés ne sont pas fiables »), sans en faire une question. Un lien peut viser une page dont l'adresse ou le titre contient le nom ; le texte du lien décrit son contenu. Seules les exceptions de la table restent : la ligne DORA et les produits du Lab quand la carte porte sur eux.
- Les objets de l'équipe et de l'interface gardent leur nom exact (« flyer », statuts « Nouvelle », « À l'étude », « En attente »).
- Les rôles sont épicènes, aucune formule n'associe l'insertion à une contrainte, et aucune instance politique n'est nommée sans besoin.
- Un cas isolé ne sert pas de preuve, et une fonctionnalité non livrée se dit engagée (« engage l'interconnexion », pas « s'interconnecte désormais »).
- Est actif qui pose un acte métier : candidature émise, orientation, recherche de service. Une connexion ou une ouverture d'email n'est pas un acte.

## 5. Cibles : ce qui compte pour chaque métier

Une cible se choisit sur son métier (accompagne-t-elle des personnes qui ont un frein ?), jamais sur sa présence actuelle sur la plateforme.

| Cible | Ce qui compte pour elle | Ce qui la fait décrocher |
|---|---|---|
| Professionnels qui accompagnent (CCAS, missions locales, structures AHI, SPIP, délégataires RSA, CIDFF, Carsat) | trouver vite le bon relais pour une personne, savoir où en est la demande, ne rien ressaisir ; garder une trace de la demande et suivre la réponse, même quand ils ont déjà appelé le service | l'explication de l'insertion à des professionnels de l'insertion ; un outil de plus présenté comme tel ; une candidature en SIAE proposée pour une personne orientée vers un service social, qui n'est pas forcément éligible à l'IAE ni prête pour l'emploi |
| Conseillers France Travail, en plus de la ligne précédente | proposer des candidatures et orienter sans quitter l'outil, puis suivre les deux au même endroit | plusieurs envois à la fois : un même conseiller entre dans plusieurs séquences, et une autre équipe lui écrit aussi sur les fins de contrat |
| Structures d'insertion (SIAE : ACI, AI, EI, ETTI ; EA, ESAT) | des candidatures traitées à temps, leur expertise reconnue, des résultats chiffrés ; leur réputation auprès des prescripteurs et des candidats, qui tient à des réponses rapides ; des candidatures précises (motivations, disponibilités, besoins d'accompagnement). Leurs CIP n'ont pas à tout porter seuls : un service peut prendre le relais de leur accompagnement, pendant le parcours ou à sa fin | être réduites à leur statut social ; « vente » au lieu de « développement commercial » ; la théorie ; rdv-insertion présenté sans dire qu'il est gratuit |
| Conseils départementaux et France Travail | les délais d'orientation des allocataires du RSA, la coordination des acteurs du territoire, l'exemple d'autres départements | le ton de start-up ; la comparaison entre collectivités ; la gratuité présentée comme un privilège |
| Têtes de réseau et unions (UDCCAS, fédérations) | un rôle de relais simple et précis, la charge prise par l'équipe, une présentation pendant une réunion déjà prévue | une demande d'« accord » ; un texte qui ne parle pas de leur réseau |
| Directions et décideurs (directions régionales, DGA) | un chiffre national sourcé, une proposition commune, un document court à transmettre | une demande qui ne tient pas compte de leur niveau |
| Acheteurs publics (marchés, clauses sociales) | leurs obligations (SPASER, clauses sociales du Code de la commande publique), des fournisseurs fiables, moins de temps de sourcing | opposer le social à l'économique ; la morale ; les sigles non expliqués |
| Entreprises et cabinets (RSE, OETH) | la déduction OETH, le reporting RSE, un panel de fournisseurs plus large | la morale sociale ; des contraintes de coût minimisées |
| Communes et leurs services (cabinet, communication, protocole) | l'événement de leur calendrier (vœux, repas des aînés), un choix qu'elles peuvent présenter publiquement | un rôle genré (« le maire ») ; une instance politique nommée sans besoin |

**Compter une cible.** La cible se compte dans le CRM Attio avec la skill `attio` : les structures (`companies`, dont `type_de_compte` et le département) et leurs contacts (`people`, dont `job_title`, `role` et `source_import`). Les contacts de prospection, jamais contactés, portent le statut « Prospect » ; un contact qui utilise déjà un produit a « Actif » sur l'attribut de ce produit (`les_emplois_de_l_inclusion`, `dora`...).

- Lire les valeurs possibles d'un attribut avant de filtrer (`--attributes companies --options type_de_compte`), traduire la demande en filtres (types de structure, départements, fonctions visées, statut), les écrire dans le cadrage, puis donner l'effectif : nombre de structures et nombre de contacts, répartis par fonction ou par département.
- Pour choisir la cible, les totaux et les répartitions suffisent. Une liste nominative se sort quand la campagne en a besoin, par exemple pour relire la cible avec le bizdev ou vérifier qu'un réseau y est.
- Les contacts qui utilisent déjà le produit proposé sortent d'une prospection, et les désinscrits de toute campagne.
- La campagne prête se dépose dans la base Notion « Campagnes à valider » (section 12).

**Registre.** Vers une direction ou un élu, la demande se formule plus formellement (« n'hésitez pas à me communiquer son nom »), et la salutation passe par la civilité et le nom quand la demande le prévoit. Un non-décideur reçoit de quoi convaincre sa hiérarchie : un document court à transmettre, comme un flyer ou une note d'une page. Les sigles s'écrivent en entier à la première mention.

**Moments qui justifient un envoi.** L'urgence vient d'un fait du calendrier de la cible, jamais d'une formule comme « Dernière chance ».

- Fin d'année : repas des aînés, arbre de Noël, vœux de janvier, fin de l'exercice budgétaire.
- Février : rapports d'activité et dialogues de gestion des SIAE.
- Rentrée : réorganisation des équipes.
- Novembre : Semaine européenne pour l'emploi des personnes handicapées, Mois de l'ESS.
- À partir du 16/11/2026 : l'orientation se fait depuis La plateforme de l'inclusion.
- Une échéance propre au contact, tirée des données : date de sortie d'une candidature, carnets financés dans son département.

## 6. Mots du métier et sigles

Les professionnels de l'insertion ont leur vocabulaire, et un texte qui leur est adressé l'emploie : c'est leur langage courant, pas un jargon à traduire.

| Mot | Sens et usage |
|---|---|
| Frein, lever un frein | Difficulté qui éloigne de l'emploi en dehors du poste : mobilité, logement, santé, garde d'enfants, français, démarches. Le terme se garde tel quel et ne se remplace pas par « un problème à régler ». Les freins se lèvent aussi pendant l'emploi : un texte ne fait pas attendre qu'ils soient tous levés pour parler d'emploi. |
| Bénéficiaire, personne accompagnée | La personne que le professionnel suit. Les conseillers France Travail disent aussi « demandeur d'emploi », et les libellés de l'application disent « usager ». |
| Orientation vers un service d'insertion | Adresser une personne à un service (mobilité, logement, santé…) avec sa situation ; le service accepte, refuse ou demande des précisions, et la demande se clôt sans réponse au bout de 30 jours. Jamais « orientation » seule. |
| Candidature, mise en relation avec un employeur solidaire | Proposer une personne à une structure d'insertion ou à un employeur inclusif pour un poste. |
| Éligibilité à l'IAE | Condition pour entrer dans un parcours en SIAE, validée par un prescripteur habilité. Une personne orientée vers un service social n'est pas forcément éligible, ni prête pour l'emploi. |
| PASS IAE | Agrément qui ouvre le parcours en SIAE. Sa fin et celle du contrat de travail ne coïncident pas toujours : un texte dit laquelle il vise. |
| Prescripteur habilité, orienteur | Un prescripteur habilité (France Travail, mission locale, Cap emploi, conseil départemental…) valide l'éligibilité à l'IAE ; un orienteur propose des candidatures sans la valider. |
| Offreur de services | Structure qui référence ses services. Les offreurs continuent de les référencer dans DORA après le 16/11/2026. |

Sigles, à écrire en entier à la première mention dans un texte destiné à l'extérieur :

- IAE, SIAE : insertion par l'activité économique ; structure d'insertion par l'activité économique, qui regroupe ACI (atelier et chantier d'insertion), AI (association intermédiaire), EI (entreprise d'insertion) et ETTI (entreprise de travail temporaire d'insertion).
- GEIQ : groupement d'employeurs pour l'insertion et la qualification. EA, ESAT : entreprise adaptée ; établissement et service d'aide par le travail.
- CIP : conseiller en insertion professionnelle, souvent le premier destinataire en SIAE.
- CD : conseil départemental, chef de file du RSA. bRSA : bénéficiaires du RSA.
- CCAS, CIAS, UDCCAS : centre communal ou intercommunal d'action sociale ; leur union départementale.
- AHI : accueil, hébergement, insertion (CHRS, CHU, CADA, CPH, HUDA, résidences sociales, foyers de jeunes travailleurs, pensions de famille).
- SPIP : service pénitentiaire d'insertion et de probation. CIDFF : centre d'information sur les droits des femmes et des familles. Carsat : caisse d'assurance retraite et de la santé au travail.
- RPE : réseau pour l'emploi. DIHAL : délégation interministérielle à l'hébergement et à l'accès au logement.
- SPASER : schéma de promotion des achats socialement et écologiquement responsables. Clauses sociales : heures d'insertion réservées dans un marché public.

## 7. L'application vue par un professionnel

Relevé des 21 et 22/10/2026. Un texte destiné aux utilisateurs reprend ces libellés entre guillemets, à la lettre. Un libellé qui ne figure pas ici se vérifie dans le code public `gip-inclusion/les-emplois` ou s'écrit « à vérifier ».

**Menus.**

- Prescripteur : « Accueil » ; « Demandes envoyées », avec « Candidatures vers des emplois » et « Orientations vers des services » ; « Accompagnements », avec « Usagers accompagnés » ; « Organisation », avec « Collaborateurs » ; « Rechercher », avec « Un emploi inclusif », « Un service d'insertion » et « Un accompagnement ».
- Employeur (SIAE, GEIQ, employeur inclusif) : « Accueil » ; « Demandes reçues » ; « Demandes envoyées » ; « Accompagnements » ; « Structure », avec « Fiche de présentation », « Fiches de poste » et « Collaborateurs » ; « Rechercher ».
- « Accueil » ouvre la page « Tableau de bord » : c'est le tableau de bord dont parlent les emails de l'équipe.

**Comportements qu'un texte décrit souvent.**

- Le prescripteur reçoit un email quand la structure ou le service répond, et retrouve la réponse dans « Demandes envoyées ». Les coordonnées d'une structure figurent dans le détail de la candidature.
- Une même personne peut être proposée à plusieurs structures en même temps. La structure qui répond vite la rencontre avant qu'elle s'engage ailleurs, et un refus motivé aide le prescripteur à chercher une autre piste.
- Un lien vers une page de l'application passe par la connexion, et la personne n'arrive pas toujours ensuite sur la page visée : un bouton se teste connecté et déconnecté avant l'envoi.
- Un professionnel dont l'espace n'est rattaché à aucune structure n'accède pas aux fonctions professionnelles. Si ses collègues sont inscrits, l'un d'eux l'ajoute depuis « Organisation » (« Structure » pour un employeur), « Collaborateurs » ; sinon il inscrit sa structure avec son numéro SIRET.
- La recherche d'un service demande une ville et une thématique. Sur la fiche d'un service, le bouton s'appelle « Orienter votre usager en ligne ».
- Dans « Fiches de poste », un poste passe de « Ouvert » à « Fermé » : un poste fermé ne reçoit plus de candidatures.

**Emails que l'application envoie déjà.** L'application envoie 98 emails transactionnels (candidatures, PASS IAE, organisations et membres, fiches de poste, orientations), sans email d'accueil. Les comptes Brevo des produits ont aussi leurs séquences d'accueil pour les prescripteurs et les employeurs. Avant de concevoir un envoi vers un public, ces emails et les séquences des autres équipes se listent, pour qu'une personne ne reçoive pas deux messages sur le même sujet. La skill `brevo` les lit, avant d'écrire : `--templates` et `--sends` sur les comptes `emplois` et `dora` pour les emails des produits, `--campaigns` sur le compte `marketing` pour les campagnes récentes de l'équipe et leurs dates. Le cadrage écrit « à vérifier » seulement si la skill `brevo` ne répond pas.

**Ce qu'on dit en externe.** Le narratif conseille « Orienter, suivre et piloter au même endroit », « DORA reste l'outil de recherche » et « suivre toutes vos demandes au même endroit ». Il proscrit, en plus des mots de la section 4, « DORA disparaît » et « Votre nouveau compte » pour quelqu'un qui en a déjà un.

## 8. Ce qui a fait répondre et agir

Constats tirés des campagnes de la PDI, sur de petits effectifs :

- **La première phrase dit d'où vient le contact.** « Le Conseil départemental [...] nous a transmis les coordonnées de votre structure » a obtenu le meilleur taux de réponse de la série.
- **Une tête de réseau reçoit un rôle précis, et la charge reste chez l'expéditeur** : la campagne vers les unions de CCAS construite ainsi a obtenu des rendez-vous.
- **L'appel à l'action suit ce que la campagne veut obtenir.** Quand l'acte se fait dans l'outil, le bouton y mène. Une offre vendue en rendez-vous garde le rendez-vous.
- **Une échéance propre à la personne, dite à plat** : au singulier, l'email a été environ deux fois plus cliqué qu'au pluriel.
- **Le canal peut compter plus que le texte** : sur des têtes de réseau, LinkedIn a obtenu beaucoup plus de réponses que l'email du même texte.
- **La relation de l'expéditeur compte plus que la forme** : une campagne écrite avec des formules convenues a obtenu des réponses et des rendez-vous parce que le réseau connaissait l'expéditeur. Les règles de ce fichier servent à éviter les retouches, pas à garantir les réponses.
- **Un email fait refaire un geste connu ; un geste nouveau demande plus** : une campagne qui proposait un premier acte n'a converti qu'une petite part de ses destinataires.

Ouvertures et clics ne prouvent rien seuls : des robots de sécurité ouvrent les emails, et LGM compte les messages d'absence parmi les réponses. Un effet se compte en actes métier. Août est une période de congés pour l'équipe comme pour les cibles.

## 9. Tournures à retirer

Un motif se retire quand il gêne la lecture ; il reste quand il sert le ton (section 2).

| Motif | Avant | Après |
|---|---|---|
| Image à la place du fait | « Un frein connu vient de sauter » | « rdv-insertion engage l'interconnexion avec ces logiciels de parcours » |
| Outil ou idée en sujet | « La plateforme rend cette suite lisible » | « Sur La plateforme de l'inclusion, chaque orientation reste visible au même endroit » |
| Trois éléments pour le rythme, objet compris | « gratuite, publique, sans engagement » | « un service public gratuit, ouvert sans marché à passer » |
| Famille « suffit » | « il vous suffit de passer la candidature en attente » ; « un mot en réponse suffit » | « vous pouvez passer la candidature en attente » ; « Seriez-vous d'accord pour en parler 15 minutes ? » |
| Reprise, inversion, litote | « Votre place, elle, n'a jamais bougé » | « Votre place est bien réservée » |
| « C'est exactement ce que… » | « C'est exactement ce que règle votre espace » | le fait, sans annonce |
| Négation construite | « non pas à tout le monde, mais à chacune pour un besoin repéré » | « à chacune, pour un besoin repéré » |
| Clôture qui parle de la boîte ou de l'envoi | « Nous ne voulons pas encombrer votre boîte » ; « Ce sera mon dernier message » | une clôture qui aide à décider de la suite : fin réelle des relances, aide encore disponible |
| Pathos de clôture | « le travail que vous faites compte » | « Bon courage à vos équipes ! » |
| Sécheresse | demande à l'impératif, sans formule de fin | « pourriez-vous », « souhaitez-vous », puis « Belle journée, » |
| « On » et mots-béquilles | « On en parle 15 minutes ? » ; « en clair », « concrètement » | « nous » ou une tournure impersonnelle ; supprimés |
| Demande imagée ou ambiguë | « Pourriez-vous m'ouvrir 30 minutes lors d'une prochaine réunion ? » ; « nous ouvrir un temps de présentation » ; « il n'y a qu'un créneau à ouvrir » | « Accepteriez-vous que je présente ces résultats à vos adhérents lors d'une de vos réunions ? Il nous faudrait une trentaine de minutes, et nous préparons tout. » |
| Paragraphe bloc | quatre phrases ou plus qui enchaînent un constat, des chiffres, leurs causes et les corrections | une phrase d'annonce, puis un fait par ligne ; un paragraphe par idée |
| Rôle genré, contrainte, instance politique | « Le maire peut alors présenter ce choix » ; « préparés en insertion » | « La municipalité peut ensuite présenter ce choix » ; « contribuant à l'insertion » |

L'objet et le préheader se relisent seuls, avant le corps : aucune triade, aucune image, ni « on » ni tiret long, et le préheader ne répète pas l'objet.

Le texte ne gagne ni chiffre, ni souvenir, ni sentiment ajouté pour le rendre vivant. Si la matière manque, il reste sobre et le manque se signale à part.

**Passe humanizer, avant de rendre.** Un email peut éviter tous les motifs du tableau et se lire quand même comme généré, à cause de sa forme : le paragraphe bloc et la demande imagée du tableau, et surtout la symétrie (antithèse en miroir, négation suivie d'un fragment, trois éléments parallèles, question posée pour y répondre, formule de clôture qui résume). Demander au modèle de « sonner humain » remplace l'essai lisse par des fragments et des retournements, aussi repérables. La voix attendue est faite de phrases complètes de longueur inégale, qui avancent par des faits.

Chaque paragraphe passe ensuite trois tests. Lu à voix haute, il doit sonner comme une explication que la personne qui signe donnerait au téléphone. Son idée se dit en une phrase simple ; sinon il se scinde. Si l'on remplace le nom du produit ou du réseau par un autre et que le paragraphe reste vrai, il ne dit rien de précis et se réécrit avec un fait.

Quand le bizdev a écrit ses brouillons, la passe part de son texte : elle garde ses phrases, son ordre et ses listes, et ne retire que les motifs nommés de cette section. Chaque phrase retirée ou changée se justifie par un motif, ou se pose comme question à part.

## 10. Exemples

Les textes sont cités tels qu'ils sont partis, parfois en extrait, liens abrégés. Un exemple se reprend pour sa mécanique, jamais phrase à phrase, et la ligne « À reprendre aujourd'hui » dit ce que les règles de ce fichier y changent.

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

À reprendre aujourd'hui : « La plateforme de l'inclusion » dans sa casse ; « créer votre compte » sort ; le lien vise une page profonde avec `mtm_` ; la salutation suit la section 3 (`<var name="customAttribute1" default="Bonjour,"/>`), et les autres variables aussi.

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

À reprendre aujourd'hui : DORA ne se nomme plus, l'objet et le corps décrivent l'acte dans La plateforme de l'inclusion ; la dernière relance annonce la fin des relances et pose une dernière question utile. « Nous ouvrir un temps de présentation » et « il n'y a qu'un créneau à ouvrir » se disent sans image : présenter l'outil aux adhérents lors d'une réunion déjà prévue.

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

À reprendre aujourd'hui : « le garder sous la main » et « il vous suffit de » sortent ; le lien vise une page profonde de `plateforme.inclusion.gouv.fr`, avec `mtm_` ; la salutation suit la section 3, avec sa virgule et sans emoji.

### Activation : un brouillon et sa correction par la responsable du contenu

Un extrait du brouillon :

```
Objet : Proposer une candidature en quelques minutes

Votre espace sur la plateforme de l'inclusion est ouvert depuis deux jours.

Depuis votre tableau de bord :
- chercher un emploi inclusif près de chez elle ;
- ouvrir le poste qui lui correspond et cliquer sur Postuler ;
- valider son éligibilité, puisque votre agence est habilitée ;
- suivre la réponse de l'employeur dans Demandes envoyées.
```

Le même passage corrigé :

```
Bienvenue sur La plateforme de l'inclusion !

Depuis votre tableau de bord :
- cherchez un emploi inclusif près de chez elle ;
- ouvrez le poste qui lui correspond et cliquez sur « Postuler » ;
- validez son éligibilité à l'IAE : en tant que prescripteur, vous êtes habilité à le faire ;
- suivez la réponse de l'employeur dans « Demandes envoyées ».

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

## 11. Relecture avant de rendre

Relire chaque email en entier : l'objet et le préheader d'abord, seuls, puis le corps, de la salutation à la signature. Un contrôle vaut « oui » quand tout le brouillon le respecte, « non » dès qu'une ligne le viole. Chaque « non » se corrige avant de rendre.

1. **Cadrage.** L'en-tête est complet et conforme à la demande : même produit, même acte, même cible, même expéditeur. Le livrable est celui que la demande attend ; un point ouvert autre que la cible ou l'acte figure comme hypothèse dans le cadrage, sans réduire le livrable.
2. **Fond intact.** Le texte d'un tiers est repris mot pour mot, et quand le bizdev a écrit ses brouillons, chaque email part de son texte : une phrase retirée ou changée l'est pour un motif de la section 9 ou figure dans les questions ; l'offre, les chiffres et les faits de la demande n'ont pas changé ; rien de la conversation n'apparaît dans les emails.
3. **Faits.** Chaque chiffre a une source datée ; une fonctionnalité non livrée est dite engagée ; une date est identique dans l'objet, le corps et le lien ; aucun cas isolé ne sert de preuve.
4. **Noms.** La table de la section 4 est respectée : « La plateforme de l'inclusion » dans sa casse, aucun ancien produit, ni « compte » ni « annuaire », « orientation » jamais seule.
5. **Variables et salutation.** Les variables existent, la salutation a sa valeur de repli, et aucun nom ni aucune adresse de destinataire ne figure dans le brouillon.
6. **Canal.** Brevo : signature écrite identique à l'expéditeur, pied complet, aucun expéditeur générique sous 2 000 destinataires (section 3). LGM : relances sans objet, corps sans signature ni désinscription, aucun « accord » ni intérêt passé présenté comme un engagement. Nulle part un nom d'étape « step N ».
7. **Liens.** Un lien sur la première mention du service, vers une page profonde, avec le suivi `mtm_` ; aucun lien provisoire.
8. **Appel à l'action et structure.** Un seul par email, adapté au genre. Un angle nouveau à chaque relance ; en relation, une seule porte de sortie par séquence et une clôture qui annonce la fin des relances avec une dernière question, sans parler de la boîte du destinataire.
9. **Ton.** Selon le genre (section 2). Aucun tiret long et les mots du métier gardés, objet et préheader compris. Un « on » ou un motif de la section 9 ne vaut « non » que s'il rend le texte sec, artificiel ou maladroit. Aucun paragraphe ne dépasse trois phrases, plusieurs faits passent en liste, chaque paragraphe passe les trois tests de la passe humanizer, et la demande dit sans image qui fait quoi, devant qui et combien de temps.
10. **Connotation.** Les rôles sont épicènes, aucune formule n'associe l'insertion à une contrainte, aucune instance politique n'est nommée sans besoin, et aucun mot ne peut blesser la cible.

## 12. Livraison

Le livrable se donne dans la conversation, dans cet ordre :

1. Le cadrage de la section 1.
2. Les emails complets pour un cas représentatif de l'audience, avec les variables résolues : salutation, paragraphes, liens, formule de fin et signature visibles.
3. Le gabarit technique ci-dessous, prêt à charger par le growth.
4. Le tableau des dix contrôles de la section 11, avec leur verdict.
5. Les questions de fond qui restent (offre, ciblage, choix de l'auteur), à part, cinq au plus, chacune avec l'option que le brouillon applique déjà.

```
# <nom de la campagne>
Demande ou carte PDI : <titre> (<id>)
Genre : relation | activation · valide : <qui>
Produit et acte : La plateforme de l'inclusion · <acte>
Cible : <métier> · <liste ou audience> (<n> contacts au <date>, ou « à compter »)
Outil : Brevo, compte marketing | LGM
Expéditeur : <nom affiché>
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

La campagne est prête quand les dix contrôles valent « oui » et qu'aucune question ne bloque. L'agent la dépose alors dans la base Notion « Campagnes à valider » (https://app.notion.com/p/41b5f321b604817eae26ef63156da10f) avec la skill `notion` : une page par campagne, avec les propriétés Campagne, Statut « À valider », Outil, Genre, Cible (les critères), Départements, Structures, Contacts, Expéditeur et Conversation Autometa, et dans le corps le livrable ci-dessus. Dans la page, l'email s'écrit en paragraphes simples, sans citation ni bloc de code. La réponse donne le lien de la page et rappelle en une phrase que le growth valide avant tout chargement, et que rien ne part sans lui.
