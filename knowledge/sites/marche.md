# Marche

- URL: https://lemarche.inclusion.gouv.fr
- Matomo site ID: 136
- Tag Manager: yes (both Google Tag Manager and Matomo Tag Manager)
- GitHub: https://github.com/gip-inclusion/le-marche

## Traffic Baselines (2025)

Data retrieved 2026-01-06 via Matomo API.

### Monthly Visitor Stats

| Month   | Unique Visitors | Visits    | Daily Avg Visitors | Daily Avg Visits |
|---------|-----------------|-----------|--------------------|-----------------:|
| 2025-01 |          28,898 |    33,722 |                932 |            1,088 |
| 2025-02 |          21,643 |    25,755 |                773 |              920 |
| 2025-03 |          28,709 |    33,216 |                926 |            1,071 |
| 2025-04 |          21,464 |    25,829 |                715 |              861 |
| 2025-05 |          17,485 |    20,873 |                564 |              673 |
| 2025-06 |          18,037 |    21,804 |                601 |              727 |
| 2025-07 |          17,435 |    20,475 |                562 |              660 |
| 2025-08 |          14,215 |    15,830 |                459 |              511 |
| 2025-09 |          20,032 |    23,076 |                668 |              769 |
| 2025-10 |          24,337 |    27,977 |                785 |              902 |
| 2025-11 |          23,396 |    27,129 |                780 |              904 |
| 2025-12 |          19,967 |    23,027 |                644 |              743 |

**Typical range:** 459-932 unique visitors/day, 511-1,088 visits/day.

### Engagement Metrics

| Month   | Bounce Rate | Actions/Visit | Avg Time on Site |
|---------|-------------|---------------|------------------|
| 2025-01 |         68% |           2.7 |           1m 36s |
| 2025-02 |         64% |           2.8 |           1m 48s |
| 2025-03 |         66% |           2.6 |           2m 22s |
| 2025-04 |         64% |           2.8 |           1m 46s |
| 2025-05 |         64% |           2.6 |           1m 34s |
| 2025-06 |         64% |           2.8 |           1m 43s |
| 2025-07 |         64% |           2.9 |           1m 47s |
| 2025-08 |         69% |           2.5 |           1m 25s |
| 2025-09 |         69% |           2.7 |           1m 35s |
| 2025-10 |         73% |           2.5 |           1m 29s |
| 2025-11 |         72% |           2.4 |           1m 37s |
| 2025-12 |         72% |           2.5 |           1m 37s |

## Custom Dimensions

| ID | Index | Scope  | Name             | Notes                                          |
|----|-------|--------|------------------|------------------------------------------------|
| 1  | 1     | visit  | User Type        | SIAE, BUYER, PARTNER, INDIVIDUAL, ADMIN        |
| 2  | 2     | visit  | User Type Detail | Combines user kind + detail (e.g., "Acheteur : Grand groupe") |

### User Type Distribution (Dec 2025)

Based on dimension 1 values (logged-in users only):

| User Type  | Visits | Actions/Visit | Bounce Rate |
|------------|--------|---------------|-------------|
| SIAE       | 458    | 11.2          | 17%         |
| BUYER      | 222    | 8.2           | 23%         |
| INDIVIDUAL | 86     | 22.3          | 8%          |
| PARTNER    | 79     | 9.1           | 14%         |
| ADMIN      | 68     | 5.0           | 32%         |

**Note:** Most traffic is anonymous (~96% of visits). Logged-in users represent a small fraction but have much higher engagement.

### User Type Detail Distribution (Dec 2025)

Top values from dimension 2:

| User Type Detail                           | Visits |
|--------------------------------------------|--------|
| Structure                                  | 458    |
| Particulier                                | 80     |
| Acheteur : Etablissement public            | 64     |
| Acheteur                                   | 62     |
| Administrateur : Etablissement public      | 45     |
| Acheteur : Grand groupe                    | 44     |
| Acheteur : Collectivite                    | 37     |
| Partenaire : Facilitateur clauses sociales | 25     |

## Saved Segments

*Retrieved 2026-01-06 via Matomo API.*

| Name | Definition |
|------|------------|
| ACTION - Recherche non loggée | `eventAction=@recherche;dimension1!@A;dimension1!@E` |
| EXIT - Tally | `outlinkUrl=@tally` |
| PROFILE - Acheteurs + déposer un besoin | `form_name==tender-create-survey-form,dimension1=@BUYER` |
| PROFILE - BUYER | `dimension1==buyer;outlinkUrl!@tally` |
| PROFILE - INDIVIDUAL | `dimension1==INDIVIDUAL` |
| PROFILE - SIAE | `dimension1==SIAE` |
| RETENTION - dernière visite 30j | `daysSinceLastVisit<32;daysSinceLastVisit>=1` |
| RETENTION - dernière visite 30j - Acheteurs | `dimension2=@Acheteur;daysSinceLastVisit<32;daysSinceLastV...` |
| RETENTION - dernière visite 30j - Structures | `daysSinceLastVisit<32;dimension2=@structure;daysSinceLast...` |
| RETENTION NON PRO - dernière visite 30j | `daysSinceLastVisit<32;daysSinceLastVisit>=1;outlinkUrl=@t...` |

## Goals

| ID | Name                              | Match Attribute | Pattern                                      |
|----|-----------------------------------|-----------------|----------------------------------------------|
| 4  | Inscription utilisateur           | event_action    | Inscription                                  |
| 5  | Publication de besoin             | event_action    | Publier et diffuser le besoin                |
| 6  | Afficher les coordonnees          | event_action    | Clic afficher les coordonnees - fiche commerciale |
| 7  | Telecharger la liste              | event_action    | Clic telecharger la liste - valoriser achats |
| 8  | Recherche                         | event_action    | Clic rechercher - Moteur recherche           |
| 9  | Consultation tableau de bord      | url             | https://lemarche.inclusion.beta.gouv.fr/besoins/ |

## Matomo Events

Events are tracked primarily via **Matomo Tag Manager**, not direct code instrumentation. The Tag Manager automatically captures link clicks with detailed context.

### Event Categories

| Category        | Events (Dec 2025) | Description                                |
|-----------------|-------------------|--------------------------------------------|
| All link clicks | ~10,700           | Automatic link click tracking via Tag Manager |
| Clic bouton     | ~2,100            | Button click events                        |
| Clic lien       | ~1,000            | Specific link click events                 |
| Formulaire      | ~350              | Form submission events                     |

### Event Tracking Implementation

- **Matomo Tag Manager:** Tracks all link clicks automatically with format:
  `{link_text} -- {page_url} -- {css_classes} -- {element_id}`
- **Custom dimensions:** Set via `_paq.push` in template for logged-in users
- **Consent:** Uses Tarteaucitron for cookie consent management

### Top Event Actions (Dec 2025)

| Action                                        | Events |
|-----------------------------------------------|--------|
| Clic rechercher - Moteur recherche            | 1,170  |
| Clic website SIAE - fiche commerciale         | 995    |
| Clic recherche SIRET - Moteur recherche       | 785    |
| Rechercher un fournisseur (homepage)          | 628    |
| Se connecter (header)                         | 312    |
| Completer votre fiche (dashboard)             | 194    |
| Inscription                                   | 170    |
| Publier un besoin d'achat (homepage)          | 114    |

### Business Context Event Categories

#### Clic bouton (Button clicks)
Manual event tracking for key business actions:

| Action                                    | Description                     |
|-------------------------------------------|---------------------------------|
| Clic rechercher - Moteur recherche        | Main search button              |
| Clic recherche SIRET - Moteur recherche   | SIRET-specific search           |
| Clic sourcing inverse - Header            | Reverse sourcing feature        |
| Clic trouver un facilitateur - Header     | Find facilitator button         |
| Clic Publier un besoin - Resultats recherche | Post need from search results |
| Clic valoriser vos achats - Header        | Purchase valorization           |
| Clic Calculer mon impact - Calcul impact  | Social impact calculator        |
| Publier et diffuser le besoin             | Publish tender (goal trigger)   |

#### Formulaire (Form submissions)
Multi-step form tracking:

| Action                  | Description                    |
|-------------------------|--------------------------------|
| Inscription             | User registration form         |
| Depot de besoin - Step 1| Tender creation wizard step 1  |
| Depot de besoin - Step 3| Tender creation wizard step 3  |
| Depot de besoin - Step 4| Tender creation wizard step 4  |

#### Clic lien (Specific link clicks)
Tracked link interactions:

| Action                              | Description                    |
|-------------------------------------|--------------------------------|
| Clic website SIAE - fiche commerciale | Click to SIAE external website |

### Notes

- Events use Matomo Tag Manager container for automatic tracking
- Most events are auto-captured link clicks with detailed context
- Button clicks (`Clic bouton`) appear to be manually configured in Tag Manager
- Form events (`Formulaire`) track multi-step wizard progression
- Goals are triggered by specific event actions (search, registration, tender publication)
