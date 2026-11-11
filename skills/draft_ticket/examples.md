# Exemples de tickets

Tirés de vrais tickets, réécrits dans la forme du skill.

## Exemple 1 : règle de gestion, sans maquette

```
# Masquer aux employeurs les candidatures non acceptées de plus de 2 ans

:autometa: Les employeurs gardent à vie l'accès aux candidatures qu'ils n'ont pas acceptées, donc aux données personnelles des candidats. Pour limiter la conservation de ces données, on veut leur retirer cet accès au bout de 2 ans, sans rien changer pour les candidats et les prescripteurs.

## Périmètre
- Utilisateurs : employeurs
- Écrans / parcours : liste des candidatures reçues, formulaire d'ajout au vivier

## Attendu
- Une candidature non acceptée (tous les statuts sauf « acceptée ») créée il y a plus de 2 ans n'est plus visible par l'employeur. Elle reste conservée, et visible pour le candidat et le prescripteur.
- Dans le formulaire d'ajout au vivier : « Les candidatures placées en vivier seront automatiquement masquées au bout de 2 ans. »
- En bas de la liste des candidatures : « Les informations détaillées sur la conservation des candidatures sont disponibles dans notre documentation. », avec un lien vers l'article du centre d'aide.

## À trancher
- Prévenir les employeurs avant le premier masquage ? (PM)

## Pistes techniques évoquées
- L'autrice note qu'un masquage manuel des candidatures existait pour les employeurs : il pourrait être réutilisé en l'automatisant.
```

## Exemple 2 : irritant remonté par le support, solution à concevoir

```
# Rendre compréhensibles les champs NIR, NIA et NTT de la fiche salarié

:autometa: Des employeurs demandent au support de remplacer un NIR par un NIA ou un NTT sur des dossiers qui n'en ont pas besoin. À la saisie de la fiche salarié, ils ne comprennent pas qu'un NIA est accepté comme un numéro de sécurité sociale : ils cochent « impossible de renseigner le numéro de sécurité sociale », ressaisissent le même NIA, puis sont bloqués parce que ce n'est pas un NTT.

## Périmètre
- Utilisateurs : employeurs (SIAE)
- Écrans / parcours : saisie de la fiche salarié, champs NIR, NIA et NTT

## Attendu
- Solution à concevoir par l'UX.
- À la fin, un employeur qui dispose d'un NIA le saisit sans passer par « impossible de renseigner le numéro de sécurité sociale ».

## Sources
- Remontée support : <lien>
```

## Exemple 3 : maquette existante

```
# Inciter les professionnels à activer la double authentification

:autometa: La CNIL recommande l'authentification à deux facteurs, et son absence pourrait être reprochée lors d'un contrôle. Une partie des professionnels y sera obligée (ticket lié). On veut inciter tous les autres à l'activer dès maintenant, avant de la rendre obligatoire pour tous.

## Périmètre
- Utilisateurs : professionnels connectés, non soumis à l'obligation, qui n'ont pas encore activé la double authentification
- Écrans / parcours : bandeau en haut de page, parcours de configuration

## Attendu
- Un bandeau en haut de page invite à activer la double authentification ; un clic ouvre le parcours de configuration.
- Une fois activée, elle est exigée à chaque connexion de cet utilisateur.
- Maquette : <lien Figma>

## À trancher
- Le bandeau peut-il être fermé ? Si oui, quand réapparaît-il ? (UX, PM)
```

## Contre-exemples

- Un ticket de 1 000 mots qui recopie l'analyse, les chiffres et l'historique des décisions. Le ticket dit ce qu'il faut faire ; le reste va dans un lien.
- Un ticket où l'agent invente une solution technique que personne n'a évoquée. Les pistes évoquées dans l'entrée vont dans « Pistes techniques évoquées », attribuées ; jamais dans le titre ni l'ouverture.
- Un ticket qui garde le ton de l'entrée (« bon du coup », « comme dit untel », « je pense que peut-être »).
- Un ticket où « À trancher » liste des questions évidentes ou rhétoriques pour avoir l'air complet.
- Un titre qui décrit le problème (« Les employeurs sont perdus ») au lieu du changement.
