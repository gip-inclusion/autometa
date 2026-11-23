"""Les graphiques Mermaid que l'agent écrit, dessinés par la page d'un rapport."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

CHARTS = {
    "xychart": (
        'xychart-beta\n    title "Candidatures acceptées par région"\n'
        '    x-axis ["Île-de-France", "Bretagne", "Réunion"]\n    y-axis "Candidatures" 0 --> 500\n'
        "    bar [420, 180, 95]\n    line [400, 200, 90]",
        "Candidatures acceptées par région",
    ),
    "flowchart": (
        'flowchart LR\n    subgraph parcours["Parcours du candidat"]\n'
        '        A["Diagnostic réalisé"] -->|"éligible"| B{"Pass IAE délivré ?"}\n    end\n'
        '    B -->|oui| C(["Embauche déclarée"])\n    B -.->|non| D["Réorientation"]',
        "Diagnostic réalisé",
    ),
    "quadrant": (
        "quadrantChart\n    title Priorité des régions\n    x-axis Faible volume --> Fort volume\n"
        "    y-axis Faible taux --> Fort taux\n    quadrant-1 À consolider\n    quadrant-2 À étudier\n"
        "    quadrant-3 À surveiller\n    quadrant-4 À développer\n    Bretagne: [0.3, 0.7]\n    Mayotte: [0.8, 0.2]",
        "Priorité des régions",
    ),
    # Why: la grammaire sankey de Mermaid refuse tout caractère non ASCII, accents compris.
    "sankey": (
        "sankey-beta\nCandidatures recues,Acceptees,120\nCandidatures recues,Refusees,60\nAcceptees,Embauches declarees,90",
        "Candidatures recues",
    ),
    "pie": (
        'pie title Répartition des prescripteurs\n    "Habilités" : 62\n    "Orienteurs" : 30\n    "Autres" : 8',
        "Répartition des prescripteurs",
    ),
    "gantt": (
        "gantt\n    title Déploiement\n    dateFormat YYYY-MM-DD\n    section Préparation\n"
        "    Recette métier :a1, 2026-01-05, 10d\n    section Lancement\n    Ouverture générale :after a1, 5d",
        "Recette métier",
    ),
    "sequence": (
        "sequenceDiagram\n    participant P as Prescripteur\n    participant E as Employeur\n"
        "    P->>E: Candidature envoyée\n    E-->>P: Réponse reçue",
        "Candidature envoyée",
    ),
    "treemap": (
        'treemap-beta\n"Structures"\n    "Ateliers et chantiers": 40\n    "Entreprises d\'insertion": 25\n    "Régies de quartier": 5',
        "Ateliers et chantiers",
    ),
    "er": (
        "erDiagram\n    CANDIDAT ||--o{ CANDIDATURE : dépose\n    CANDIDATURE }o--|| STRUCTURE : reçoit\n"
        '    CANDIDAT {\n        string nom "prénom et nom"\n    }',
        "dépose",
    ),
    "state": (
        "stateDiagram-v2\n    [*] --> Déposée\n    Déposée --> Étudiée : ouverture\n"
        "    Étudiée --> Acceptée\n    Étudiée --> Refusée\n    Acceptée --> [*]",
        "Étudiée",
    ),
    "mindmap": (
        "mindmap\n  root((Écosystème))\n    Hébergement\n      Centres d'accueil\n    Emploi\n      Structures d'insertion",
        "Hébergement",
    ),
}


@pytest.mark.parametrize(("source", "label"), CHARTS.values(), ids=CHARTS.keys())
def test_a_report_draws_the_chart_its_agent_wrote(
    source: str, label: str, visit: Callable[[str], None], page: Page, report: Callable[[str], int]
):
    visit(f"/rapports/{report(f'Avant le graphique.\n\n```mermaid\n{source}\n```\n')}")
    drawing = page.locator("#reportBody .mermaid svg")
    expect(drawing).to_contain_text(label, timeout=15_000)
    expect(drawing).not_to_have_attribute("aria-roledescription", "error")


def test_a_flowchart_follows_the_direction_its_author_wrote(
    visit: Callable[[str], None], page: Page, report: Callable[[str], int]
):
    source = (
        'flowchart TB\n    subgraph s1["Scénario un"]\n        A["Saisie"] --> B["Contrôle"]\n    end\n'
        '    subgraph s2["Scénario deux"]\n        C["Dépôt"] --> D["Réponse"]\n    end'
    )

    visit(f"/rapports/{report(f'```mermaid\n{source}\n```\n')}")
    nodes = page.locator("#reportBody .mermaid svg g.node")
    expect(nodes).to_have_count(4, timeout=15_000)
    first, second = (nodes.filter(has_text=label).bounding_box() for label in ("Saisie", "Contrôle"))
    assert second["y"] > first["y"] + first["height"]
    expect(nodes.first.locator("rect, path").first).to_have_css("fill", "rgb(236, 236, 255)")


def test_a_wide_flowchart_scrolls_in_its_frame_at_a_readable_size(
    visit: Callable[[str], None], page: Page, report: Callable[[str], int]
):
    steps = " --> ".join(f'E{n}["Étape numéro {n} du parcours"]' for n in range(12))

    visit(f"/rapports/{report(f'```mermaid\nflowchart LR\n    {steps}\n```\n')}")
    frame = page.locator("#reportBody .mermaid")
    label = frame.locator("svg g.node").filter(has_text="Étape numéro 11").locator("p, text").first
    expect(label).to_be_visible(timeout=15_000)
    sizes = page.evaluate(
        """() => {
            const frame = document.querySelector('#reportBody .mermaid');
            const label = [...frame.querySelectorAll('g.node p, g.node text')].at(-1);
            return {
                label: label.getBoundingClientRect().height,
                frame: [frame.scrollWidth, frame.clientWidth],
                page: [document.documentElement.scrollWidth, document.documentElement.clientWidth],
            };
        }"""
    )
    assert sizes["label"] >= 14
    assert sizes["frame"][0] > sizes["frame"][1]
    assert sizes["page"][0] <= sizes["page"][1]
