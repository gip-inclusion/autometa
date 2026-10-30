# Rédiger un ticket du backlog — plan d'implémentation

> **Pour les agents :** exécuter tâche par tâche via superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** dans le chat d'autometa, transformer une entrée brute (notes, vocal transcrit, fil Slack, lien Figma) en ticket court du Backlog unifié, le montrer, puis le créer dans Notion après l'accord explicite de l'auteur.

**Architecture :** la logique vit dans `lib/` (`figma.py`, `backlog.py`, `backlog_stockage.py`, `backlog_creation.py`) pour être réutilisée plus tard par un bot Slack. Le skill `skills/rediger_ticket/` porte la consigne de rédaction et cinq scripts minces qui appellent `lib/`. Un cron quotidien range le contexte des équipes (équipes actives, épics actifs, titres récents) dans `dashboard_storage` ; l'auteur et les doublons se lisent en temps réel.

**Pile :** Python 3.14, httpx, client Notion `lib/notion.py` (API `2022-06-28`), `lib.dashboard_api.query_storage`, API REST Figma (jeton de plan en lecture seule), pytest + pytest-mock, lanceur de crons existant.

**Conception :** interne (dépôt privé `organisation-produit`, `exploration/redacteur-tickets/conception.md`). La consigne a été mise au point sur un banc de 26 tickets réels, avec des juges à l'aveugle ; le banc reste dans le dépôt privé.

**Tests :** `uv run --frozen pytest tests/<fichier> -q -m "not integration"`, puis `make test` et `make lint` à la fin.

**Zones critiques :** aucune n'est modifiée. `lib/notion.py` et `lib/dashboard_api.py` (zone secondaire) sont seulement appelés.

---

**Attestations (paved road) :** un critère se prouve par des tests nommés `test_dod_<n>_…`, lancés par `uv run --frozen pytest <fichiers> -k dod_<n>` (l'outil refuse `python -m`). Le rouge et le vert s'apparient par critère, pas par commande. Chaque commit sous `lib/`, `skills/` ou `tests/` périme les verts précédents : `make paved-road-reprove` les rejoue en fin de parcours (tâche 9). En tâche 7, rejouer les verts de DOD-1 et DOD-3 avec les tests des scripts en plus : `uv run --frozen pytest tests/test_figma.py tests/test_rediger_ticket_scripts.py -k dod_1` et `uv run --frozen pytest tests/test_backlog.py tests/test_rediger_ticket_scripts.py -k dod_3`.

## Contraintes globales

- Lecture d'environnement uniquement dans `web/config.py` (règle TID251).
- `httpx` avec un `timeout=` explicite ; pas de f-string dans les appels `logger.*`.
- Docstrings d'une ligne ; pas de commentaire qui dit ce que fait le code.
- Tests : `mocker`, `parametrize`, fonctions-fabriques plutôt que fixtures ; chaque test vérifie un comportement.
- Domaine en français, technique en anglais. Messages de commit en anglais.
- Dépôt public : aucun identifiant Notion en dur (variables d'environnement), aucune donnée réelle dans les tests (clés Figma et identifiants inventés).
- Branche paved road `louije/feat/rediger-ticket` ; commits sur cette branche ; **jamais de `git push`** (l'utilisateur ouvre la PR).
- Aucune écriture dans Notion pendant le développement, sauf le test de la tâche 1 et le smoke de la tâche 12, chacun avec l'accord de l'utilisateur.

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `paved-road/rediger-ticket/definition-of-done.md` (créer) | l'accord écrit, premier commit |
| `web/config.py` (modifier, près de `NOTION_TAGS_DB`) | `NOTION_BACKLOG_DB`, `NOTION_ANNUAIRE_DB`, `FIGMA_ACCESS_TOKEN` |
| `.env.example` (modifier, section Notion) | les trois variables, commentées |
| `lib/figma.py` (créer) | lien → fichier et nœud ; cadres et textes visibles ; une image par cadre |
| `lib/backlog.py` (créer) | lecture du backlog : requêtes paginées, contexte des équipes, doublons, auteur |
| `lib/backlog_stockage.py` (créer) | contexte rangé dans `dashboard_storage` ; point d'entrée du cron |
| `lib/backlog_creation.py` (créer) | propriétés autorisées, marqueur `:autometa:`, création de la page |
| `skills/rediger_ticket/SKILL.md` (créer) | déroulé et consigne de rédaction |
| `skills/rediger_ticket/exemples.md` (créer) | trois exemples et des contre-exemples |
| `skills/rediger_ticket/maquette.md` (créer) | comment lire une maquette |
| `skills/rediger_ticket/scripts/{contexte,maquette,doublons,auteur,creer}.py` (créer) | interfaces en ligne de commande pour l'agent |
| `cron/contexte-backlog/CRON.md`, `cron/contexte-backlog/cron.py` (créer) | cron quotidien, lot `synchros` |
| `tests/test_figma.py`, `tests/test_backlog.py`, `tests/test_backlog_stockage.py`, `tests/test_backlog_creation.py`, `tests/test_rediger_ticket_scripts.py` (créer) | tests unitaires |

---

### Tâche 0 : Definition of Done (paved road)

**Fichiers :**
- Créer : `paved-road/rediger-ticket/definition-of-done.md`

- [ ] **Étape 1 : créer la branche**

```bash
git switch -c louije/feat/rediger-ticket
```

- [ ] **Étape 2 : écrire la DoD** (format : `docs/paved-road/l0-definition-of-done.md`)

```markdown
# Rédiger un ticket du backlog depuis le chat d'autometa

## Ce que je veux

Dans le chat d'autometa, je colle des notes, un vocal transcrit, un fil Slack ou un lien Figma,
et je demande un ticket. L'agent me propose un ticket court du Backlog unifié : un titre, un
paragraphe d'ouverture marqué `:autometa:`, puis Périmètre, Attendu, À trancher, Pistes
techniques évoquées et Sources. Il recommande l'équipe, le statut, le type, l'épic et la
propriété où m'inscrire, et me pose au plus trois questions. Il lit la maquette Figma. Il ne crée
le ticket qu'après mon accord.

## Ce qui devra marcher

DOD-1 — Un lien Figma vers un cadre donne, pour chaque cadre, son nom, ses textes visibles et une
image que l'agent peut regarder ; un lien sans cadre précis n'est pas lu, et l'agent le dit.

DOD-2 — Le contexte des équipes (équipes produit actives, épics actifs, titres de tickets récents)
est rangé chaque jour, et relu dans Notion s'il a plus d'un jour.

DOD-3 — Les tickets proches d'un titre proposé sont retrouvés et classés ; l'auteur est inscrit dans
`POM`, `UX`, `Développeurs` ou `Contributeurs` selon son rôle et l'équipe destinataire.

DOD-4 — Le ticket créé porte le titre, le corps, l'équipe, le statut, le type, l'épic et la
maquette ; jamais Priorité, Période ni Estimation ; un statut d'avancement de développement
(Ce sprint, En cours, En prod…) est refusé.

DOD-5 — Rien n'est écrit dans Notion sans `--go` : sans lui, le script montre seulement ce qui
serait créé.

## Décisions (validées le 2026-10-30)

1. Le marqueur `:autometa:` devient l'emoji personnalisé de l'espace. Essai du 2026-10-30 dans une
   page bac à sable : l'API accepte la mention `custom_emoji` dans un texte.
2. Âge maximal du contexte rangé avant relecture dans Notion : un jour.
3. Un ticket proche est signalé quand son titre partage au moins la moitié des mots-clés du titre
   proposé, et au moins deux ; l'agent ne montre que ceux qu'il juge vraiment proches. Mesuré le
   2026-10-30 sur 150 titres du backlog : 37 % ont au moins un candidat, contre 66 % avec « deux
   mots en commun ».
4. Maquette : 6 cadres au plus, images de 1 600 pixels de large au plus.
5. Auteur absent de l'Annuaire : l'agent lui demande son rôle. Sans compte Notion : le ticket est
   créé sans auteur inscrit, et l'agent le dit.
```

- [ ] **Étape 3 : faire valider les décisions par l'utilisateur, puis committer**

```bash
git add paved-road/rediger-ticket/definition-of-done.md
git commit -m "Add the definition of done for drafting backlog tickets"
```

---

### Tâche 1 : vérifier l'emoji personnalisé dans un texte (essai, sans code livré)

**Fait le 2026-10-30** : la mention `{"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": …}}}` est acceptée et relue telle quelle (`plain_text` : `:autometa:`). Rien à refaire ; la tâche reste pour mémoire.

But : savoir si l'API accepte une mention d'emoji personnalisé dans un `rich_text`. L'emoji `autometa` existe dans l'espace ; `GET /v1/custom_emojis` le liste (vérifié le 2026-10-30).

- [ ] **Étape 1 : demander à l'utilisateur une page bac à sable** partagée avec l'intégration, et son accord pour y créer puis archiver une sous-page de test.

- [ ] **Étape 2 : lancer l'essai** (remplacer `<PAGE_BAC_A_SABLE>` par l'identifiant donné)

```bash
.venv/bin/python - <<'EOF'
from lib import notion
emojis = notion.notion_request("GET", "custom_emojis?page_size=100")["results"]
emoji_id = next(e["id"] for e in emojis if e["name"] == "autometa")
page = notion.notion_request("POST", "pages", {
    "parent": {"page_id": "<PAGE_BAC_A_SABLE>"},
    "properties": {"title": {"title": [{"text": {"content": "Essai emoji autometa"}}]}},
    "children": [{"type": "paragraph", "paragraph": {"rich_text": [
        {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": emoji_id}}},
        {"type": "text", "text": {"content": " essai"}},
    ]}}],
})
blocs = notion.notion_request("GET", f"blocks/{page['id']}/children")["results"]
print(blocs[0]["paragraph"]["rich_text"][0])
notion.notion_request("PATCH", f"pages/{page['id']}", {"archived": True})
EOF
```

Attendu : soit la mention est relue (type `mention`, sous-type `custom_emoji`), soit une erreur 400 `validation_error`.

- [ ] **Étape 3 : consigner le résultat** dans la DoD (décision 1). Si l'API refuse, la fonction `placer_marqueur` de la tâche 6 garde le texte littéral : supprimer alors la branche `if emoji_id` et le test `test_dod_4_placer_marqueur_insere_l_emoji`, et retirer `emoji_autometa`.

---

### Tâche 2 : configuration

**Fichiers :**
- Modifier : `web/config.py` (à côté de `NOTION_TAGS_DB`, vers la ligne 179)
- Modifier : `.env.example` (section `# Notion`, vers la ligne 96)

- [ ] **Étape 1 : ajouter les variables dans `web/config.py`**

```python
NOTION_BACKLOG_DB = os.getenv("NOTION_BACKLOG_DB")
NOTION_ANNUAIRE_DB = os.getenv("NOTION_ANNUAIRE_DB")
FIGMA_ACCESS_TOKEN = os.getenv("FIGMA_ACCESS_TOKEN")
```

- [ ] **Étape 2 : documenter dans `.env.example`**, sous `# NOTION_TOKEN=secret_...`

```bash
# NOTION_BACKLOG_DB=<identifiant de la base « Backlog unifié »>
# NOTION_ANNUAIRE_DB=<identifiant de la base « Annuaire des membres »>

# ===========================================
# Figma (lecture des maquettes, jeton de plan en lecture seule, en-tête X-Figma-Token)
# ===========================================
# FIGMA_ACCESS_TOKEN=figd_...
```

- [ ] **Étape 3 : vérifier et committer**

Run: `uv run --frozen ruff check web/config.py`
Expected: `All checks passed!`

```bash
git add web/config.py .env.example
git commit -m "Add Notion backlog, member directory and Figma settings"
```

---

### Tâche 3 : lecture des maquettes Figma (`lib/figma.py`) — DOD-1

**Fichiers :**
- Créer : `lib/figma.py`
- Test : `tests/test_figma.py`

- [ ] **Étape 1 : écrire les tests**

```python
from lib import figma

CLE = "A" * 22
BRANCHE = "B" * 22


def noeud(type_, nom="n", enfants=None, texte=None, visible=True, largeur=None, id_="1:1"):
    n = {"id": id_, "type": type_, "name": nom, "children": enfants or []}
    if texte is not None:
        n["characters"] = texte
    if not visible:
        n["visible"] = False
    if largeur is not None:
        n["absoluteBoundingBox"] = {"width": largeur, "height": 100}
    return n


@pytest.mark.parametrize(
    ("url", "attendu"),
    [
        (f"https://www.figma.com/design/{CLE}/Maquette?node-id=4524-5330&t=x", figma.LienFigma(CLE, "4524:5330", "design")),
        (f"https://www.figma.com/board/{CLE}/Notifications?t=x", figma.LienFigma(CLE, None, "board")),
        (f"https://www.figma.com/design/{CLE}/x/branch/{BRANCHE}/x?node-id=1-5", figma.LienFigma(BRANCHE, "1:5", "design")),
        ("https://exemple.fr/design/abc", None),
    ],
)
def test_analyser_lien(url, attendu):
    assert figma.analyser_lien(url) == attendu


def test_dod_1_textes_visibles_ignore_les_calques_masques():
    cadre = noeud("FRAME", enfants=[
        noeud("TEXT", texte="Titre"),
        noeud("GROUP", visible=False, enfants=[noeud("TEXT", texte="Ancien texte")]),
        noeud("TEXT", texte="  "),
        noeud("TEXT", texte="Bouton"),
    ])
    assert figma.textes_visibles(cadre) == ["Titre", "Bouton"]


@pytest.mark.parametrize(
    ("racine", "noms"),
    [
        (noeud("FRAME", nom="Écran"), ["Écran"]),
        (noeud("SECTION", nom="S", enfants=[noeud("FRAME", nom="Vue pro"), noeud("FRAME", nom="Vue candidat")]), ["Vue pro", "Vue candidat"]),
        (noeud("CANVAS", enfants=[noeud("FRAME", nom=str(i)) for i in range(8)]), ["0", "1", "2", "3", "4", "5"]),
        (noeud("CANVAS", enfants=[noeud("FRAME", nom="masqué", visible=False), noeud("FRAME", nom="visible")]), ["visible"]),
    ],
)
def test_choisir_cadres(racine, noms):
    assert [c["name"] for c in figma.choisir_cadres(racine)] == noms


def test_dod_1_lire_cadres_sans_noeud_ne_lit_rien(mocker):
    appel = mocker.patch.object(figma, "appeler_api")
    assert figma.lire_cadres(figma.LienFigma(CLE, None, "board")) == []
    appel.assert_not_called()


def test_dod_1_lire_cadres_donne_nom_textes_et_largeur(mocker):
    document = noeud("SECTION", enfants=[noeud("FRAME", nom="Choix 1", id_="2:2", largeur=1435, enfants=[noeud("TEXT", texte="Accepter la candidature")])])
    mocker.patch.object(figma, "appeler_api", return_value={"nodes": {"4:5": {"document": document}}})
    cadres = figma.lire_cadres(figma.LienFigma(CLE, "4:5", "design"))
    assert cadres == [figma.Cadre(id="2:2", nom="Choix 1", textes=["Accepter la candidature"], largeur=1435)]


def test_dod_1_exporter_images_reduit_la_largeur_et_ecrit_le_png(mocker, tmp_path):
    appel = mocker.patch.object(figma, "appeler_api", return_value={"images": {"2:2": "https://rendu/2-2.png"}})
    reponse = mocker.Mock(content=b"PNG")
    mocker.patch.object(figma.httpx, "get", return_value=reponse)
    cadre = figma.Cadre(id="2:2", nom="Choix 1", textes=[], largeur=3200)
    images = figma.exporter_images(figma.LienFigma(CLE, "4:5", "design"), [cadre], tmp_path)
    assert appel.call_args.args[1]["scale"] == 0.5
    assert images == {"2:2": tmp_path / "cadre-1.png"}
    assert (tmp_path / "cadre-1.png").read_bytes() == b"PNG"


def test_appeler_api_envoie_le_jeton_de_plan(mocker):
    mocker.patch.object(figma.config, "FIGMA_ACCESS_TOKEN", "jeton")
    get = mocker.patch.object(figma.httpx, "get", return_value=mocker.Mock(json=lambda: {"ok": True}))
    assert figma.appeler_api("files/x/nodes", {"ids": "1:2"}) == {"ok": True}
    assert get.call_args.kwargs["headers"] == {"X-Figma-Token": "jeton"}
    assert get.call_args.kwargs["timeout"] == figma.TIMEOUT
```

Ajouter `import pytest` en tête du fichier.

- [ ] **Étape 2 : journaliser le rouge**

Run: `make paved-road-advance DOD=DOD-1 RED=1 CMD='uv run --frozen pytest tests/test_figma.py -k dod_1'`
Expected: échec à l'import (`cannot import name 'figma'`).

- [ ] **Étape 3 : écrire `lib/figma.py`**

```python
"""Lecture seule des maquettes Figma : cadres, textes visibles et images."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from web import config

logger = logging.getLogger(__name__)

API = "https://api.figma.com/v1"
TIMEOUT = 30
TYPES_CADRE = {"FRAME", "SECTION", "COMPONENT", "COMPONENT_SET"}
TYPES_ECRAN = {"FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"}
LIEN = re.compile(
    r"figma\.com/(?P<genre>design|file|board|proto)/(?P<cle>[0-9A-Za-z]{22,128})"
    r"(?:/[^/?]*/branch/(?P<branche>[0-9A-Za-z]{22,128}))?"
)
NOEUD = re.compile(r"[?&]node-id=(\d+)[-:](\d+)")


@dataclass(frozen=True)
class LienFigma:
    cle: str
    noeud: str | None
    genre: str


@dataclass(frozen=True)
class Cadre:
    id: str
    nom: str
    textes: list[str]
    largeur: float


def analyser_lien(url: str) -> LienFigma | None:
    """Fichier, nœud et genre d'un lien Figma, ou None si ce n'en est pas un."""
    lien = LIEN.search(url)
    if not lien:
        return None
    noeud = NOEUD.search(url)
    return LienFigma(
        cle=lien.group("branche") or lien.group("cle"),
        noeud=f"{noeud.group(1)}:{noeud.group(2)}" if noeud else None,
        genre="board" if lien.group("genre") == "board" else "design",
    )


def textes_visibles(noeud: dict) -> list[str]:
    """Textes des calques visibles, dans l'ordre du document."""
    if noeud.get("visible") is False:
        return []
    texte = noeud.get("characters", "").strip()
    textes = [texte] if texte else []
    for enfant in noeud.get("children", []):
        textes.extend(textes_visibles(enfant))
    return textes


def choisir_cadres(noeud: dict, maximum: int = 6) -> list[dict]:
    """Le nœud s'il est un écran, sinon ses cadres enfants visibles."""
    if noeud.get("type") in TYPES_ECRAN:
        return [noeud]
    enfants = [e for e in noeud.get("children", []) if e.get("type") in TYPES_CADRE and e.get("visible") is not False]
    return (enfants or [noeud])[:maximum]


def appeler_api(chemin: str, params: dict | None = None) -> dict:
    """GET sur l'API Figma avec le jeton de plan."""
    reponse = httpx.get(
        f"{API}/{chemin}",
        params=params,
        headers={"X-Figma-Token": config.FIGMA_ACCESS_TOKEN or ""},
        timeout=TIMEOUT,
    )
    reponse.raise_for_status()
    return reponse.json()


def lire_cadres(lien: LienFigma, maximum: int = 6) -> list[Cadre]:
    """Cadres du nœud lié, avec leurs textes visibles."""
    if not lien.noeud:
        return []
    document = appeler_api(f"files/{lien.cle}/nodes", {"ids": lien.noeud})["nodes"][lien.noeud]["document"]
    return [
        Cadre(
            id=cadre["id"],
            nom=cadre.get("name", ""),
            textes=textes_visibles(cadre),
            largeur=(cadre.get("absoluteBoundingBox") or {}).get("width") or 0,
        )
        for cadre in choisir_cadres(document, maximum)
    ]


def exporter_images(lien: LienFigma, cadres: list[Cadre], dossier: Path, largeur_max: int = 1600) -> dict[str, Path]:
    """Une image PNG par cadre, réduite à largeur_max pixels, rangée par identifiant de cadre."""
    dossier.mkdir(parents=True, exist_ok=True)
    images = {}
    for rang, cadre in enumerate(cadres, start=1):
        echelle = round(min(1.0, largeur_max / cadre.largeur), 3) if cadre.largeur else 1.0
        url = appeler_api(f"images/{lien.cle}", {"ids": cadre.id, "format": "png", "scale": echelle})["images"].get(cadre.id)
        if not url:
            logger.warning("Figma n'a pas rendu le cadre %s", cadre.id)
            continue
        image = httpx.get(url, timeout=TIMEOUT)
        image.raise_for_status()
        chemin = dossier / f"cadre-{rang}.png"
        chemin.write_bytes(image.content)
        images[cadre.id] = chemin
    return images
```

- [ ] **Étape 4 : lancer les tests**

Run: `uv run --frozen pytest tests/test_figma.py -q`
Expected: `13 passed`

- [ ] **Étape 5 : committer et attester**

```bash
git add lib/figma.py tests/test_figma.py
git commit -m "Read Figma frames, visible texts and frame renders"
make paved-road-advance DOD=DOD-1 CMD='uv run --frozen pytest tests/test_figma.py -k dod_1'
```

---

### Tâche 4 : lecture du backlog (`lib/backlog.py`) — DOD-2 et DOD-3

**Fichiers :**
- Créer : `lib/backlog.py`
- Test : `tests/test_backlog.py`

- [ ] **Étape 1 : écrire les tests**

```python
import pytest

from lib import backlog


def titre_notion(texte):
    return {"type": "title", "title": [{"plain_text": texte}]}


def relation(*ids):
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def page(id_, titre, statut=None, url="", **relations):
    proprietes = {"Nom": titre_notion(titre)}
    if statut:
        proprietes["Statut"] = {"type": "select", "select": {"name": statut}}
    for nom, ids in relations.items():
        proprietes[nom.replace("_", " ")] = relation(*ids)
    return {"id": id_, "url": url, "properties": proprietes}


def reponse(*pages, suite=None):
    return {"results": list(pages), "has_more": suite is not None, "next_cursor": suite}


def test_requeter_pagine_et_s_arrete_a_la_limite(mocker):
    appel = mocker.patch(
        "lib.notion.notion_request",
        side_effect=[reponse(page("a", "A"), page("b", "B"), suite="c1"), reponse(page("c", "C"), suite="c2")],
    )
    lignes = backlog.requeter("base", {"property": "x"}, limite=3)
    assert [p["id"] for p in lignes] == ["a", "b", "c"]
    assert appel.call_args_list[1].args[2]["start_cursor"] == "c1"
    assert appel.call_count == 2


def test_dod_2_charger_contexte_regroupe_epics_et_titres_par_equipe(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    schema = {"properties": {
        "Pizza team": {"relation": {"database_id": "equipes"}},
        "Epic - feuille de route": {"relation": {"database_id": "epics"}},
    }}

    def notion(methode, chemin, charge=None):
        if methode == "GET":
            return schema
        base = chemin.split("/")[1]
        return {
            "equipes": reponse(page("e1", "Prescription "), page("e2", "Emplois")),
            "epics": reponse(page("p1", "DORA - RUN", Pizza_team=["e1"]), page("p2", "RUN EMPLOIS", Pizza_team=["e2"])),
            "backlog": reponse(page("t1", "Modale DORA", Pizza_team=["e1"]), page("t2", "Fiche salarié", Pizza_team=["e2"]), page("t3", "", Pizza_team=["e2"])),
        }[base]

    mocker.patch("lib.notion.notion_request", side_effect=notion)
    contexte = backlog.charger_contexte()
    assert contexte["equipes"] == [
        {"id": "e1", "nom": "Prescription", "epics": [{"id": "p1", "nom": "DORA - RUN"}], "tickets_recents": ["Modale DORA"]},
        {"id": "e2", "nom": "Emplois", "epics": [{"id": "p2", "nom": "RUN EMPLOIS"}], "tickets_recents": ["Fiche salarié"]},
    ]


def test_formater_contexte_trie_les_equipes_et_liste_epics_et_tickets():
    contexte = {"genere_le": "2026-10-30T02:00:00+00:00", "equipes": [
        {"id": "e2", "nom": "Prescription", "epics": [], "tickets_recents": ["Modale DORA"]},
        {"id": "e1", "nom": "Emplois", "epics": [{"id": "p", "nom": "RUN EMPLOIS"}], "tickets_recents": []},
    ]}
    assert backlog.formater_contexte(contexte) == (
        "# Équipes produit actives (au 2026-10-30)\n\n"
        "## Emplois\n- Épics actifs : RUN EMPLOIS\n- Tickets récents :\n\n"
        "## Prescription\n- Tickets récents :\n  - Modale DORA\n"
    )


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("Masquer aux employeurs les candidatures non acceptées", ["Masquer", "employeurs", "candidatures", "acceptées"]),
        ("Afficher une modale pour les prescripteurs", ["modale", "prescripteurs"]),
        ("le la de", []),
    ],
)
def test_mots_cles(texte, attendu):
    assert backlog.mots_cles(texte) == attendu


def test_dod_3_chercher_doublons_classe_et_ecarte_les_rapprochements_faibles(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=reponse(
            page("a", "Masquer les candidatures des employeurs", statut="Cadrage", url="u-a"),
            page("b", "Candidatures : export CSV", statut="Métier", url="u-b"),
            page("c", "Masquer candidatures employeurs non acceptées", statut="Bac à sable 🏝️", url="u-c"),
        ),
    )
    trouves = backlog.chercher_doublons("Masquer aux employeurs les candidatures non acceptées")
    assert [t["url"] for t in trouves] == ["u-c", "u-a"]
    assert trouves[0] == {"titre": "Masquer candidatures employeurs non acceptées", "url": "u-c", "statut": "Bac à sable 🏝️", "communs": 4}


def test_dod_3_chercher_doublons_exige_la_moitie_des_mots_cles(mocker):
    mocker.patch.object(backlog.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch(
        "lib.notion.notion_request",
        return_value=reponse(
            page("a", "Export des candidatures employeurs", url="u-a"),
            page("b", "Export candidatures employeurs prescripteurs DDETS", url="u-b"),
        ),
    )
    trouves = backlog.chercher_doublons("Export mensuel des candidatures employeurs prescripteurs DDETS GEIQ")
    assert [t["url"] for t in trouves] == ["u-b"]


def test_dod_3_trouver_auteur_croise_annuaire_et_comptes_notion(mocker):
    mocker.patch.object(backlog.config, "NOTION_ANNUAIRE_DB", "annuaire")
    fiche = {"id": "f", "properties": {
        "Nom": titre_notion("Camille"),
        "Rôle": {"type": "multi_select", "multi_select": [{"name": "Designer"}]},
        "🍕 Équipes": relation("e1"),
    }}
    comptes = {"results": [
        {"id": "u1", "type": "person", "name": "Camille", "person": {"email": "camille@exemple.fr"}},
        {"id": "b1", "type": "bot", "name": "Robot"},
    ], "has_more": False}
    mocker.patch("lib.notion.notion_request", side_effect=[reponse(fiche), comptes])
    assert backlog.trouver_auteur("Camille@exemple.fr") == backlog.Auteur(nom="Camille", roles=["Designer"], equipes=["e1"], notion_id="u1")


@pytest.mark.parametrize(
    ("roles", "equipes_auteur", "destinataires", "champ"),
    [
        (["Responsable d'équipe"], ["e1"], ["e1"], "POM"),
        (["Responsable d'équipe"], ["e1"], ["e2"], "Contributeurs"),
        (["Designer"], ["e1"], ["e2"], "UX"),
        (["Dev"], [], ["e1"], "Développeurs"),
        (["Data analyst"], [], ["e1"], "Développeurs"),
        (["Chargé.e de déploiement"], ["e1"], ["e1"], "Contributeurs"),
        ([], [], ["e1"], "Contributeurs"),
    ],
)
def test_dod_3_champ_auteur(roles, equipes_auteur, destinataires, champ):
    auteur = backlog.Auteur(nom="x", roles=roles, equipes=equipes_auteur, notion_id="u")
    assert backlog.champ_auteur(auteur, destinataires) == champ
```

- [ ] **Étape 2 : journaliser le rouge**

Run: `make paved-road-advance DOD=DOD-3 RED=1 CMD='uv run --frozen pytest tests/test_backlog.py -k dod_3'`
Expected: échec à l'import.

- [ ] **Étape 3 : écrire `lib/backlog.py`**

```python
"""Lecture du Backlog unifié pour rédiger un ticket : équipes, épics, tickets proches, auteur."""

import logging
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime

from lib import notion
from web import config

logger = logging.getLogger(__name__)

STATUTS_EPIC_INACTIFS = ("Archivé", "𝗘𝗡 𝗣𝗥𝗢𝗗 ce trimestre")
ROLES_PM = {"Responsable d'équipe", "Gestionnaire de produit", "Product Owner", "Produit", "Responsable de Mission"}
ROLES_DESIGN = {"Designer", "Design"}
ROLES_DEV = {"Dev", "Data", "Data analyst"}
MOTS_VIDES = {
    "pour", "dans", "avec", "sans", "quand", "plus", "moins", "leur", "leurs", "cette", "afin",
    "afficher", "ajouter", "permettre", "pouvoir", "faire", "depuis", "apres", "avant", "entre",
    "tous", "toutes", "tout", "page", "ecran", "etre", "avoir", "lors", "aussi",
}


@dataclass(frozen=True)
class Auteur:
    nom: str
    roles: list[str]
    equipes: list[str]
    notion_id: str | None


def requeter(base: str, filtre: dict | None = None, tri: list[dict] | None = None, limite: int | None = None) -> list[dict]:
    """Pages d'une base Notion, filtrées et triées, jusqu'à limite."""
    pages: list[dict] = []
    curseur = None
    while True:
        charge: dict = {"page_size": 100}
        if filtre:
            charge["filter"] = filtre
        if tri:
            charge["sorts"] = tri
        if curseur:
            charge["start_cursor"] = curseur
        reponse = notion.notion_request("POST", f"databases/{base}/query", charge)
        pages.extend(reponse["results"])
        if limite and len(pages) >= limite:
            return pages[:limite]
        if not reponse.get("has_more"):
            return pages
        curseur = reponse["next_cursor"]


def titre(page: dict) -> str:
    """Titre d'une page, sans espaces aux bords."""
    return notion.extract_page_title(page).strip()


def ids_relation(page: dict, propriete: str) -> list[str]:
    """Identifiants des pages liées par une relation."""
    return [r["id"] for r in page["properties"].get(propriete, {}).get("relation", [])]


def bases_liees() -> dict[str, str]:
    """Bases Équipes et Épics, lues dans le schéma du backlog."""
    schema = notion.notion_request("GET", f"databases/{config.NOTION_BACKLOG_DB}")
    return {
        "equipes": schema["properties"]["Pizza team"]["relation"]["database_id"],
        "epics": schema["properties"]["Epic - feuille de route"]["relation"]["database_id"],
    }


def charger_contexte(par_equipe: int = 15, tickets_lus: int = 300) -> dict:
    """Équipes produit actives, avec leurs épics actifs et leurs titres de tickets récents."""
    bases = bases_liees()
    equipes = requeter(bases["equipes"], {"and": [
        {"property": "Activité", "select": {"equals": "Actif"}},
        {"property": "Type", "select": {"equals": "Équipe produit"}},
    ]})
    epics = requeter(bases["epics"], {"and": [
        {"property": "Statut", "status": {"does_not_equal": statut}} for statut in STATUTS_EPIC_INACTIFS
    ]})
    tickets = requeter(
        config.NOTION_BACKLOG_DB,
        {"property": "Statut", "select": {"does_not_equal": "Annulé"}},
        [{"timestamp": "created_time", "direction": "descending"}],
        limite=tickets_lus,
    )
    return {
        "genere_le": datetime.now(UTC).isoformat(),
        "equipes": [
            {
                "id": equipe["id"],
                "nom": titre(equipe),
                "epics": [{"id": e["id"], "nom": titre(e)} for e in epics if equipe["id"] in ids_relation(e, "Pizza team")],
                "tickets_recents": [
                    titre(t) for t in tickets if equipe["id"] in ids_relation(t, "Pizza team") and titre(t)
                ][:par_equipe],
            }
            for equipe in equipes
        ],
    }


def formater_contexte(contexte: dict) -> str:
    """Le contexte des équipes en Markdown, pour l'agent."""
    lignes = [f"# Équipes produit actives (au {contexte['genere_le'][:10]})", ""]
    for equipe in sorted(contexte["equipes"], key=lambda e: e["nom"]):
        lignes.append(f"## {equipe['nom']}")
        if equipe["epics"]:
            lignes.append("- Épics actifs : " + " ; ".join(e["nom"] for e in equipe["epics"]))
        lignes.append("- Tickets récents :")
        lignes.extend(f"  - {t}" for t in equipe["tickets_recents"])
        lignes.append("")
    return "\n".join(lignes)


def normaliser(texte: str) -> str:
    """Texte en minuscules, sans accents."""
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()


def mots_cles(texte: str, maximum: int = 8) -> list[str]:
    """Mots porteurs de sens d'un titre, sans doublon."""
    mots: list[str] = []
    for mot in re.findall(r"[^\W\d_][\w'’-]{3,}", texte):
        if normaliser(mot) not in MOTS_VIDES and normaliser(mot) not in {normaliser(m) for m in mots}:
            mots.append(mot)
    return mots[:maximum]


def chercher_doublons(texte: str, limite: int = 5) -> list[dict]:
    """Tickets non annulés dont le titre partage au moins la moitié des mots-clés de texte (et deux), les plus proches d'abord."""
    mots = mots_cles(texte)
    if not mots:
        return []
    pages = requeter(
        config.NOTION_BACKLOG_DB,
        {"and": [
            {"property": "Statut", "select": {"does_not_equal": "Annulé"}},
            {"or": [{"property": "Nom", "title": {"contains": mot}} for mot in mots]},
        ]},
        limite=100,
    )
    cibles = {normaliser(m) for m in mots}
    # Why: avec « deux mots en commun », 66 % des titres du backlog avaient des candidats (mesure du 2026-10-30) ;
    # avec la moitié des mots-clés, 37 %, et rarement plus de cinq.
    seuil = max(2, math.ceil(len(cibles) / 2))
    notes = [(sum(1 for c in cibles if c in normaliser(titre(p))), p) for p in pages]
    notes.sort(key=lambda note: note[0], reverse=True)
    return [
        {
            "titre": titre(p),
            "url": p.get("url", ""),
            "statut": (p["properties"].get("Statut", {}).get("select") or {}).get("name", ""),
            "communs": communs,
        }
        for communs, p in notes[:limite]
        if communs >= seuil
    ]


def utilisateur_notion(email: str) -> tuple[str, str] | None:
    """Identifiant et nom du compte Notion qui porte cet e-mail."""
    curseur = None
    while True:
        reponse = notion.notion_request("GET", "users?page_size=100" + (f"&start_cursor={curseur}" if curseur else ""))
        for compte in reponse["results"]:
            if compte.get("type") == "person" and (compte.get("person") or {}).get("email", "").lower() == email.lower():
                return compte["id"], compte.get("name", "")
        if not reponse.get("has_more"):
            return None
        curseur = reponse["next_cursor"]


def trouver_auteur(email: str) -> Auteur | None:
    """Rôles et équipes de l'auteur d'après l'Annuaire, et son compte Notion."""
    fiches = requeter(config.NOTION_ANNUAIRE_DB, {"property": "Email", "email": {"equals": email}}, limite=1)
    compte = utilisateur_notion(email)
    if not fiches and not compte:
        return None
    proprietes = notion.extract_page_properties(fiches[0]) if fiches else {}
    return Auteur(
        nom=compte[1] if compte else titre(fiches[0]),
        roles=proprietes.get("Rôle") or [],
        equipes=ids_relation(fiches[0], "🍕 Équipes") if fiches else [],
        notion_id=compte[0] if compte else None,
    )


def champ_auteur(auteur: Auteur, equipes_destinataires: list[str]) -> str:
    """Propriété de personne où inscrire l'auteur, selon son rôle et l'équipe destinataire."""
    roles = set(auteur.roles)
    if roles & ROLES_PM:
        return "POM" if set(auteur.equipes) & set(equipes_destinataires) else "Contributeurs"
    if roles & ROLES_DESIGN:
        return "UX"
    if roles & ROLES_DEV:
        return "Développeurs"
    return "Contributeurs"
```

Note : l'Annuaire a un titre `Nom`, comme le backlog ; `extract_page_title` lit la première propriété de type titre, quel que soit son nom.

- [ ] **Étape 4 : lancer les tests**

Run: `uv run --frozen pytest tests/test_backlog.py -q`
Expected: `16 passed`

- [ ] **Étape 5 : committer et attester**

```bash
git add lib/backlog.py tests/test_backlog.py
git commit -m "Read team context, similar tickets and author role from the backlog"
make paved-road-advance DOD=DOD-3 CMD='uv run --frozen pytest tests/test_backlog.py -k dod_3'
```

---

### Tâche 5 : contexte rangé et cron quotidien — DOD-2

**Fichiers :**
- Créer : `lib/backlog_stockage.py`, `cron/contexte-backlog/CRON.md`, `cron/contexte-backlog/cron.py`
- Test : `tests/test_backlog_stockage.py`

- [ ] **Étape 1 : écrire les tests**

```python
from datetime import UTC, datetime, timedelta

from lib import backlog_stockage
from lib.query import QueryResult


def resultat(lignes=None):
    return QueryResult(success=True, data={"columns": ["contenu", "genere_le"], "rows": lignes or [], "row_count": len(lignes or [])})


def contexte(age):
    return {"genere_le": (datetime.now(UTC) - age).isoformat(), "equipes": []}


def test_dod_2_lire_contexte_renvoie_le_contexte_frais(mocker):
    frais = contexte(timedelta(hours=3))
    mocker.patch.object(backlog_stockage, "query_storage", side_effect=[resultat(), resultat([[frais, frais["genere_le"]]])])
    assert backlog_stockage.lire_contexte() == frais


def test_dod_2_lire_contexte_perime_renvoie_none(mocker):
    vieux = contexte(timedelta(days=2))
    mocker.patch.object(backlog_stockage, "query_storage", side_effect=[resultat(), resultat([[vieux, vieux["genere_le"]]])])
    assert backlog_stockage.lire_contexte() is None


def test_dod_2_contexte_courant_relit_notion_et_range_si_rien_n_est_frais(mocker):
    neuf = contexte(timedelta(0))
    mocker.patch.object(backlog_stockage, "lire_contexte", return_value=None)
    mocker.patch.object(backlog_stockage.backlog, "charger_contexte", return_value=neuf)
    range_ = mocker.patch.object(backlog_stockage, "enregistrer_contexte")
    assert backlog_stockage.contexte_courant() == neuf
    range_.assert_called_once_with(neuf)


def test_enregistrer_contexte_cree_la_table_puis_ecrit(mocker):
    stockage = mocker.patch.object(backlog_stockage, "query_storage", return_value=resultat())
    backlog_stockage.enregistrer_contexte(contexte(timedelta(0)))
    assert stockage.call_args_list[0].args[0] == backlog_stockage.CREER
    assert stockage.call_args_list[1].args[0] == backlog_stockage.ECRIRE
    assert '"equipes": []' in stockage.call_args_list[1].args[1]["contenu"]


def test_echec_du_stockage_leve_une_erreur(mocker):
    mocker.patch.object(backlog_stockage, "query_storage", return_value=QueryResult(success=False, data=None, error="refus"))
    with pytest.raises(RuntimeError, match="refus"):
        backlog_stockage.lire_contexte()


def test_main_sans_configuration_ne_lit_pas_notion(mocker):
    mocker.patch.object(backlog_stockage.config, "NOTION_BACKLOG_DB", None)
    charger = mocker.patch.object(backlog_stockage.backlog, "charger_contexte")
    backlog_stockage.main()
    charger.assert_not_called()
```

Ajouter `import pytest` en tête du fichier.

- [ ] **Étape 2 : journaliser le rouge**

Run: `make paved-road-advance DOD=DOD-2 RED=1 CMD='uv run --frozen pytest tests/test_backlog.py tests/test_backlog_stockage.py -k dod_2'`
Expected: échec à l'import.

- [ ] **Étape 3 : écrire `lib/backlog_stockage.py`**

```python
"""Contexte des équipes du backlog, rangé dans dashboard_storage et rafraîchi chaque jour."""

import json
import logging
from datetime import UTC, datetime, timedelta

from lib import backlog
from lib.dashboard_api import query_storage
from web import config

logger = logging.getLogger(__name__)

CREER = (
    "CREATE TABLE IF NOT EXISTS dashboard_storage.backlog_contexte "
    "(cle text PRIMARY KEY, contenu jsonb NOT NULL, genere_le timestamptz NOT NULL)"
)
ECRIRE = (
    "INSERT INTO dashboard_storage.backlog_contexte (cle, contenu, genere_le) "
    "VALUES ('courant', CAST(:contenu AS jsonb), CAST(:genere_le AS timestamptz)) "
    "ON CONFLICT (cle) DO UPDATE SET contenu = EXCLUDED.contenu, genere_le = EXCLUDED.genere_le"
)
LIRE = "SELECT contenu, genere_le FROM dashboard_storage.backlog_contexte WHERE cle = 'courant'"


def executer(sql: str, params: dict | None = None) -> dict:
    """Exécute une requête sur dashboard_storage, ou lève l'erreur qu'elle renvoie."""
    resultat = query_storage(sql, params)
    if not resultat.success:
        raise RuntimeError(f"dashboard_storage : {resultat.error}")
    return resultat.data


def enregistrer_contexte(contexte: dict) -> None:
    """Range le contexte, en remplaçant le précédent."""
    executer(CREER)
    executer(ECRIRE, {"contenu": json.dumps(contexte, ensure_ascii=False), "genere_le": contexte["genere_le"]})


def lire_contexte(age_max: timedelta = timedelta(days=1)) -> dict | None:
    """Le contexte rangé s'il a moins de age_max, sinon None."""
    executer(CREER)
    lignes = executer(LIRE)["rows"]
    if not lignes:
        return None
    contenu, genere_le = lignes[0]
    contenu = json.loads(contenu) if isinstance(contenu, str) else contenu
    genere_le = datetime.fromisoformat(genere_le) if isinstance(genere_le, str) else genere_le
    if datetime.now(UTC) - genere_le > age_max:
        return None
    return contenu


def contexte_courant() -> dict:
    """Le contexte rangé s'il est frais, sinon un contexte relu dans Notion, puis rangé."""
    contexte = lire_contexte()
    if contexte is None:
        contexte = backlog.charger_contexte()
        enregistrer_contexte(contexte)
    return contexte


def main() -> None:
    """Point d'entrée du cron quotidien."""
    if not config.NOTION_BACKLOG_DB:
        logger.warning("NOTION_BACKLOG_DB absent : contexte du backlog non rafraîchi")
        return
    contexte = backlog.charger_contexte()
    enregistrer_contexte(contexte)
    logger.info("Contexte du backlog rangé : %d équipes", len(contexte["equipes"]))
```

- [ ] **Étape 4 : écrire le cron**

`cron/contexte-backlog/CRON.md` :

```markdown
---
title: Contexte des équipes pour la rédaction de tickets
schedule: daily
timeout: 300
batch: synchros
---

Relit chaque nuit, dans le Backlog unifié, les équipes produit actives, leurs épics actifs et
leurs titres de tickets récents, et les range dans `dashboard_storage.backlog_contexte`. Le skill
`rediger_ticket` s'en sert pour recommander l'équipe et l'épic d'un ticket sans relire Notion à
chaque conversation. Le code vit dans `lib/backlog_stockage.py`.

Rien de personnel n'est rangé : des noms d'équipes, d'épics et des titres de tickets.
```

`cron/contexte-backlog/cron.py` :

```python
"""Range chaque jour le contexte des équipes du backlog pour la rédaction de tickets. Périodique."""

from lib.backlog_stockage import main
from web.cron_task import run

if __name__ == "__main__":
    run(main)
```

- [ ] **Étape 5 : lancer les tests, dont la découverte des crons**

Run: `uv run --frozen pytest tests/test_backlog_stockage.py tests/test_cron_runner.py -q -m "not integration"`
Expected: tout passe ; `repo_system_tasks()` découvre `contexte-backlog` dans le lot `synchros`.

- [ ] **Étape 6 : committer et attester**

```bash
git add lib/backlog_stockage.py cron/contexte-backlog tests/test_backlog_stockage.py
git commit -m "Store the backlog team context daily in dashboard_storage"
make paved-road-advance DOD=DOD-2 CMD='uv run --frozen pytest tests/test_backlog.py tests/test_backlog_stockage.py -k dod_2'
```

---

### Tâche 6 : création du ticket (`lib/backlog_creation.py`) — DOD-4

**Fichiers :**
- Créer : `lib/backlog_creation.py`
- Test : `tests/test_backlog_creation.py`

- [ ] **Étape 1 : écrire les tests**

```python
import pytest

from lib import backlog_creation as creation


def ticket(**champs):
    valeurs = {"titre": "Masquer les candidatures anciennes", "corps": ":autometa: Les employeurs gardent l'accès.",
               "equipes": ["e1"], "statut": "Cadrage", "types": ["Fonctionnalité"]}
    valeurs.update(champs)
    return creation.Ticket(**valeurs)


def test_dod_4_construire_proprietes_ne_pose_que_les_champs_autorises():
    proprietes = creation.construire_proprietes(ticket(figma="https://figma", epic="p1", champ_auteur="UX", auteur_notion_id="u1"))
    assert set(proprietes) == {"Nom", "Pizza team", "Statut", "Type", "Figma", "Epic - feuille de route", "UX"}
    assert proprietes["UX"] == {"people": [{"id": "u1"}]}
    assert not {"Priorité", "Période", "Estimation"} & set(proprietes)


@pytest.mark.parametrize(
    ("champs", "message"),
    [
        ({"statut": "𝗗𝗘𝗩 En prod"}, "Statut non proposable"),
        ({"statut": "𝗗𝗘𝗩 Ce sprint"}, "Statut non proposable"),
        ({"types": ["Épopée"]}, "Type inconnu"),
        ({"equipes": []}, "Au moins une équipe"),
        ({"champ_auteur": "Responsable(s)", "auteur_notion_id": "u1"}, "Champ d'auteur inconnu"),
    ],
)
def test_dod_4_construire_proprietes_refuse(champs, message):
    with pytest.raises(ValueError, match=message):
        creation.construire_proprietes(ticket(**champs))


def paragraphe(texte):
    return {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": texte}}]}}


def test_dod_4_placer_marqueur_insere_l_emoji():
    blocs = creation.placer_marqueur([paragraphe(":autometa: Les employeurs gardent l'accès.")], "emoji-1")
    textes = blocs[0]["paragraph"]["rich_text"]
    assert textes[0] == {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": "emoji-1"}}}
    assert textes[1]["text"]["content"] == " Les employeurs gardent l'accès."


def test_placer_marqueur_sans_emoji_garde_le_texte():
    blocs = creation.placer_marqueur([paragraphe(":autometa: Texte")], None)
    assert blocs[0]["paragraph"]["rich_text"][0]["text"]["content"] == ":autometa: Texte"


def test_emoji_autometa_parcourt_les_pages(mocker):
    mocker.patch("lib.notion.notion_request", side_effect=[
        {"results": [{"id": "x", "name": "autre"}], "has_more": True, "next_cursor": "c"},
        {"results": [{"id": "e", "name": "autometa"}], "has_more": False},
    ])
    assert creation.emoji_autometa() == "e"


def test_dod_4_creer_ticket_envoie_100_blocs_puis_le_reste(mocker):
    mocker.patch.object(creation.config, "NOTION_BACKLOG_DB", "backlog")
    mocker.patch.object(creation, "emoji_autometa", return_value=None)
    mocker.patch("lib.notion.markdown_to_blocks", return_value=[paragraphe(str(i)) for i in range(150)])
    appel = mocker.patch("lib.notion.notion_request", side_effect=[{"id": "p", "url": "https://notion/p"}, {}])
    assert creation.creer_ticket(ticket()) == ("p", "https://notion/p")
    creer, ajouter = appel.call_args_list
    assert creer.args[2]["parent"] == {"database_id": "backlog"}
    assert len(creer.args[2]["children"]) == 100
    assert ajouter.args[:2] == ("PATCH", "blocks/p/children")
    assert len(ajouter.args[2]["children"]) == 50
```

- [ ] **Étape 2 : journaliser le rouge**

Run: `make paved-road-advance DOD=DOD-4 RED=1 CMD='uv run --frozen pytest tests/test_backlog_creation.py -k dod_4'`
Expected: échec à l'import.

- [ ] **Étape 3 : écrire `lib/backlog_creation.py`**

```python
"""Création d'un ticket dans le Backlog unifié, après accord de l'auteur."""

import logging
from dataclasses import dataclass

from lib import notion
from web import config

logger = logging.getLogger(__name__)

MARQUEUR = ":autometa:"
NOM_EMOJI = "autometa"
# Why: Priorité, Période, Estimation et les statuts d'avancement de dev sont des décisions d'équipe.
STATUTS_PROPOSABLES = (
    "Bac à sable 🏝️", "stand-by", "𝗨𝗫 À faire", "Métier", "Cadrage",
    "𝗨𝗫/𝗗𝗘𝗩 Conception", "𝗨𝗫 Test utilisateur", "𝗨𝗫 À valider", "𝗗𝗘𝗩 Prêt à développer",
)
TYPES = ("Fonctionnalité", "Bug", "Sécurité", "Technique", "Tâche")
CHAMPS_AUTEUR = ("POM", "UX", "Développeurs", "Contributeurs")


@dataclass(frozen=True)
class Ticket:
    titre: str
    corps: str
    equipes: list[str]
    statut: str
    types: list[str]
    figma: str | None = None
    epic: str | None = None
    champ_auteur: str | None = None
    auteur_notion_id: str | None = None


def construire_proprietes(ticket: Ticket) -> dict:
    """Propriétés Notion du ticket, limitées à celles que l'auteur peut poser."""
    if ticket.statut not in STATUTS_PROPOSABLES:
        raise ValueError(f"Statut non proposable : {ticket.statut}")
    if not ticket.types or not set(ticket.types) <= set(TYPES):
        raise ValueError(f"Type inconnu : {ticket.types}")
    if not ticket.equipes:
        raise ValueError("Au moins une équipe est requise")
    proprietes = {
        "Nom": {"title": [{"text": {"content": ticket.titre[:2000]}}]},
        "Pizza team": {"relation": [{"id": e} for e in ticket.equipes]},
        "Statut": {"select": {"name": ticket.statut}},
        "Type": {"multi_select": [{"name": t} for t in ticket.types]},
    }
    if ticket.figma:
        proprietes["Figma"] = {"url": ticket.figma}
    if ticket.epic:
        proprietes["Epic - feuille de route"] = {"relation": [{"id": ticket.epic}]}
    if ticket.champ_auteur and ticket.auteur_notion_id:
        if ticket.champ_auteur not in CHAMPS_AUTEUR:
            raise ValueError(f"Champ d'auteur inconnu : {ticket.champ_auteur}")
        proprietes[ticket.champ_auteur] = {"people": [{"id": ticket.auteur_notion_id}]}
    return proprietes


def emoji_autometa() -> str | None:
    """Identifiant de l'emoji personnalisé de l'espace, s'il existe."""
    curseur = None
    while True:
        reponse = notion.notion_request("GET", "custom_emojis?page_size=100" + (f"&start_cursor={curseur}" if curseur else ""))
        for emoji in reponse.get("results", []):
            if emoji.get("name") == NOM_EMOJI:
                return emoji["id"]
        if not reponse.get("has_more"):
            return None
        curseur = reponse["next_cursor"]


def placer_marqueur(blocs: list[dict], emoji_id: str | None) -> list[dict]:
    """Remplace le marqueur en tête du premier paragraphe par l'emoji de l'espace."""
    premier = next((b for b in blocs if b.get("type") == "paragraph"), None)
    if not premier or not emoji_id:
        return blocs
    textes = premier["paragraph"]["rich_text"]
    contenu = textes[0].get("text", {}).get("content", "") if textes else ""
    if not contenu.startswith(MARQUEUR):
        return blocs
    textes[0]["text"]["content"] = contenu[len(MARQUEUR):]
    textes.insert(0, {"type": "mention", "mention": {"type": "custom_emoji", "custom_emoji": {"id": emoji_id}}})
    return blocs


def creer_ticket(ticket: Ticket) -> tuple[str, str]:
    """Crée la page du ticket et renvoie son identifiant et son URL."""
    blocs = placer_marqueur(notion.markdown_to_blocks(ticket.corps), emoji_autometa())
    page = notion.notion_request("POST", "pages", {
        "parent": {"database_id": config.NOTION_BACKLOG_DB},
        "properties": construire_proprietes(ticket),
        "children": blocs[:100],
    })
    for debut in range(100, len(blocs), 100):
        notion.notion_request("PATCH", f"blocks/{page['id']}/children", {"children": blocs[debut:debut + 100]})
    logger.info("Ticket créé dans le backlog : %s", page["id"])
    return page["id"], page["url"]
```

Si l'essai de la tâche 1 a montré une autre forme de mention, la reporter dans `placer_marqueur` et dans `test_dod_4_placer_marqueur_insere_l_emoji`.

- [ ] **Étape 4 : lancer les tests**

Run: `uv run --frozen pytest tests/test_backlog_creation.py -q`
Expected: `10 passed`

- [ ] **Étape 5 : committer et attester**

```bash
git add lib/backlog_creation.py tests/test_backlog_creation.py
git commit -m "Create backlog tickets with allowed properties and the autometa marker"
make paved-road-advance DOD=DOD-4 CMD='uv run --frozen pytest tests/test_backlog_creation.py -k dod_4'
```

---

### Tâche 7 : scripts du skill — DOD-1 et DOD-5

**Fichiers :**
- Créer : `skills/rediger_ticket/scripts/contexte.py`, `maquette.py`, `doublons.py`, `auteur.py`, `creer.py`
- Test : `tests/test_rediger_ticket_scripts.py`

- [ ] **Étape 1 : écrire les tests**

```python
import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import httpx
import pytest

from lib import backlog
from lib.figma import Cadre

SCRIPTS = Path(__file__).parent.parent / "skills/rediger_ticket/scripts"


def charger(nom):
    spec = importlib.util.spec_from_file_location(f"rediger_ticket_{nom}", SCRIPTS / f"{nom}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTEXTE = {"genere_le": "2026-10-30T02:00:00+00:00", "equipes": [
    {"id": "e1", "nom": "Emplois inclusifs et dispositifs réglementés", "epics": [{"id": "p1", "nom": "RUN EMPLOIS"}], "tickets_recents": []},
]}
AUTEUR = backlog.Auteur(nom="Camille", roles=["Responsable d'équipe"], equipes=["e1"], notion_id="u1")


def brouillon(tmp_path, **champs):
    valeurs = {"titre": "Masquer les candidatures anciennes", "corps": ":autometa: Texte.",
               "equipes": ["Emplois inclusifs et dispositifs réglementés"], "statut": "Cadrage",
               "types": ["Fonctionnalité"], "epic": "RUN EMPLOIS"}
    valeurs.update(champs)
    chemin = tmp_path / "brouillon.json"
    chemin.write_text(json.dumps(valeurs, ensure_ascii=False))
    return str(chemin)


def preparer_creer(mocker):
    creer = charger("creer")
    mocker.patch.object(creer.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    mocker.patch.object(creer.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(creer.backlog, "trouver_auteur", return_value=AUTEUR)
    creation = mocker.patch.object(creer.backlog_creation, "creer_ticket", return_value=("p", "https://notion/p"))
    return creer, creation


def test_dod_5_creer_sans_go_ne_cree_rien(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    sortie = creer.run(Namespace(brouillon=brouillon(tmp_path), go=False))
    creation.assert_not_called()
    assert sortie.startswith("Vérification seulement")
    assert '"POM"' in sortie


def test_dod_5_creer_avec_go_resout_noms_et_auteur(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    assert creer.run(Namespace(brouillon=brouillon(tmp_path), go=True)) == "Ticket créé : https://notion/p"
    ticket = creation.call_args.args[0]
    assert (ticket.equipes, ticket.epic, ticket.champ_auteur, ticket.auteur_notion_id) == (["e1"], "p1", "POM", "u1")


def test_creer_respecte_le_champ_donne_par_l_auteur(mocker, tmp_path):
    creer, creation = preparer_creer(mocker)
    creer.run(Namespace(brouillon=brouillon(tmp_path, champ_auteur="UX"), go=True))
    assert creation.call_args.args[0].champ_auteur == "UX"


@pytest.mark.parametrize(
    ("champs", "message"),
    [({"equipes": ["Équipe fantôme"]}, "Équipe inconnue"), ({"epic": "Épic fantôme"}, "Épic inconnu")],
)
def test_creer_refuse_un_nom_inconnu(mocker, tmp_path, champs, message):
    creer, _ = preparer_creer(mocker)
    with pytest.raises(ValueError, match=message):
        creer.run(Namespace(brouillon=brouillon(tmp_path, **champs), go=True))


@pytest.mark.parametrize(
    ("url", "debut"),
    [
        ("https://exemple.fr/x", "Ce n'est pas un lien Figma"),
        ("https://www.figma.com/board/AAAAAAAAAAAAAAAAAAAAAA/x", "Lien Figma sans cadre précis"),
    ],
)
def test_dod_1_maquette_ne_lit_pas_un_lien_inexploitable(mocker, url, debut):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    lire = mocker.patch.object(maquette.figma, "lire_cadres")
    assert maquette.run(Namespace(url=url)).startswith(debut)
    lire.assert_not_called()


def test_dod_1_maquette_liste_cadres_textes_et_images(mocker, tmp_path):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(maquette, "dossier_images", return_value=tmp_path)
    mocker.patch.object(maquette.figma, "lire_cadres", return_value=[Cadre(id="2:2", nom="Choix 1", textes=["Accepter"], largeur=100)])
    mocker.patch.object(maquette.figma, "exporter_images", return_value={"2:2": tmp_path / "cadre-1.png"})
    sortie = maquette.run(Namespace(url="https://www.figma.com/design/AAAAAAAAAAAAAAAAAAAAAA/x?node-id=1-2"))
    assert "## Cadre 1 : Choix 1" in sortie
    assert f"Image à regarder : {tmp_path / 'cadre-1.png'}" in sortie
    assert "- Accepter" in sortie


LIEN_CADRE = "https://www.figma.com/design/AAAAAAAAAAAAAAAAAAAAAA/x?node-id=1-2"
REQUETE = httpx.Request("GET", "https://api.figma.com")


@pytest.mark.parametrize(
    ("erreur", "attendu"),
    [
        (httpx.HTTPStatusError("403", request=REQUETE, response=httpx.Response(403)), "Maquette non lue : Figma répond 403 (accès refusé ou fichier introuvable)."),
        (httpx.HTTPStatusError("429", request=REQUETE, response=httpx.Response(429)), "Maquette non lue : Figma limite les appels (429), réessayer dans une minute."),
        (httpx.ConnectTimeout("lent", request=REQUETE), "Maquette non lue : Figma ne répond pas."),
    ],
)
def test_dod_1_maquette_dit_pourquoi_elle_n_est_pas_lue(mocker, erreur, attendu):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(maquette.figma, "lire_cadres", side_effect=erreur)
    assert maquette.run(Namespace(url=LIEN_CADRE)) == attendu


def test_dod_1_maquette_signale_un_cadre_introuvable(mocker):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(maquette.figma, "lire_cadres", return_value=[])
    assert maquette.run(Namespace(url=LIEN_CADRE)).startswith("Cadre introuvable dans ce fichier Figma")


def test_dod_1_maquette_garde_les_textes_si_les_images_echouent(mocker):
    maquette = charger("maquette")
    mocker.patch.object(maquette.config, "FIGMA_ACCESS_TOKEN", "jeton")
    mocker.patch.object(maquette.figma, "lire_cadres", return_value=[Cadre(id="2:2", nom="Choix 1", textes=["Accepter"], largeur=100)])
    mocker.patch.object(maquette.figma, "exporter_images", side_effect=httpx.ReadTimeout("lent", request=REQUETE))
    sortie = maquette.run(Namespace(url=LIEN_CADRE))
    assert "Images non rendues (Maquette non lue : Figma ne répond pas.) : se fier aux textes." in sortie
    assert "- Accepter" in sortie
    assert "Image à regarder" not in sortie


def test_auteur_sans_session_le_dit(mocker):
    auteur = charger("auteur")
    mocker.patch.object(auteur.config, "agent_user_email", return_value=None)
    assert auteur.run(Namespace(equipe=[])) == "Personne connectée inconnue : l'auteur ne sera pas inscrit."


def test_dod_3_auteur_donne_le_champ_pour_l_equipe_visee(mocker):
    auteur = charger("auteur")
    mocker.patch.object(auteur.config, "agent_user_email", return_value="camille@exemple.fr")
    mocker.patch.object(auteur.backlog, "trouver_auteur", return_value=AUTEUR)
    mocker.patch.object(auteur.backlog_stockage, "contexte_courant", return_value=CONTEXTE)
    sortie = auteur.run(Namespace(equipe=["Emplois inclusifs et dispositifs réglementés"]))
    assert "Rôles : Responsable d'équipe" in sortie
    assert "Inscrit dans : POM" in sortie


def test_contexte_rafraichi_relit_notion_et_range(mocker):
    script = charger("contexte")
    mocker.patch.object(script.backlog, "charger_contexte", return_value=CONTEXTE)
    ranger = mocker.patch.object(script.backlog_stockage, "enregistrer_contexte")
    sortie = script.run(Namespace(rafraichir=True))
    ranger.assert_called_once_with(CONTEXTE)
    assert "## Emplois inclusifs et dispositifs réglementés" in sortie


def test_dod_3_doublons_liste_les_tickets_proches(mocker):
    doublons = charger("doublons")
    mocker.patch.object(doublons.backlog, "chercher_doublons", return_value=[{"titre": "T", "url": "u", "statut": "Cadrage", "communs": 3}])
    assert doublons.run(Namespace(titre="Masquer les candidatures")) == "- T (Cadrage, 3 mots communs) u"
```

- [ ] **Étape 2 : journaliser le rouge**

Run: `make paved-road-advance DOD=DOD-5 RED=1 CMD='uv run --frozen pytest tests/test_rediger_ticket_scripts.py -k dod_5'`
Expected: échec (`FileNotFoundError` sur les scripts).

- [ ] **Étape 3 : écrire `skills/rediger_ticket/scripts/contexte.py`**

```python
"""Affiche le contexte des équipes du backlog : équipes produit actives, épics actifs, tickets récents."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog, backlog_stockage  # noqa: E402


def run(args: argparse.Namespace) -> str:
    if args.rafraichir:
        contexte = backlog.charger_contexte()
        backlog_stockage.enregistrer_contexte(contexte)
    else:
        contexte = backlog_stockage.contexte_courant()
    return backlog.formater_contexte(contexte)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rafraichir", action="store_true", help="relire Notion sans attendre le cron")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
```

- [ ] **Étape 4 : écrire `skills/rediger_ticket/scripts/maquette.py`**

```python
"""Lit une maquette Figma : cadres, textes visibles et une image par cadre à regarder."""

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import figma  # noqa: E402
from web import config  # noqa: E402


def dossier_images() -> Path:
    return Path("/tmp/rediger_ticket") / (config.agent_conversation_id() or "local")


def message_erreur(erreur: httpx.HTTPError) -> str:
    if isinstance(erreur, httpx.HTTPStatusError) and erreur.response.status_code == 429:
        return "Maquette non lue : Figma limite les appels (429), réessayer dans une minute."
    if isinstance(erreur, httpx.HTTPStatusError):
        return f"Maquette non lue : Figma répond {erreur.response.status_code} (accès refusé ou fichier introuvable)."
    return "Maquette non lue : Figma ne répond pas."


def run(args: argparse.Namespace) -> str:
    lien = figma.analyser_lien(args.url)
    if lien is None:
        return f"Ce n'est pas un lien Figma : {args.url}"
    if not lien.noeud:
        return "Lien Figma sans cadre précis (pas de node-id) : maquette non lue. Demander un lien vers le cadre."
    if not config.FIGMA_ACCESS_TOKEN:
        return "FIGMA_ACCESS_TOKEN absent : maquette non lue."
    try:
        cadres = figma.lire_cadres(lien)
    except httpx.HTTPError as erreur:
        return message_erreur(erreur)
    if not cadres:
        return "Cadre introuvable dans ce fichier Figma (supprimé, ou lien vers un autre fichier) : demander un lien vers le cadre."
    lignes = [f"# Maquette : {args.url}", ""]
    try:
        images = figma.exporter_images(lien, cadres, dossier_images() / f"{lien.cle}-{lien.noeud.replace(':', '-')}")
    except httpx.HTTPError as erreur:
        images = {}
        lignes.extend([f"Images non rendues ({message_erreur(erreur)}) : se fier aux textes.", ""])
    for rang, cadre in enumerate(cadres, start=1):
        lignes.append(f"## Cadre {rang} : {cadre.nom}")
        if cadre.id in images:
            lignes.append(f"Image à regarder : {images[cadre.id]}")
        lignes.append("Textes visibles :")
        lignes.extend(f"- {texte}" for texte in cadre.textes)
        lignes.append("")
    return "\n".join(lignes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="lien Figma vers un cadre (avec node-id)")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
```

- [ ] **Étape 5 : écrire `skills/rediger_ticket/scripts/doublons.py`**

```python
"""Cherche dans le backlog les tickets dont le titre ressemble au titre proposé."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog  # noqa: E402


def run(args: argparse.Namespace) -> str:
    trouves = backlog.chercher_doublons(args.titre)
    if not trouves:
        return "Aucun ticket proche."
    return "\n".join(f"- {t['titre']} ({t['statut']}, {t['communs']} mots communs) {t['url']}" for t in trouves)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("titre", help="titre proposé pour le ticket")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
```

- [ ] **Étape 6 : écrire `skills/rediger_ticket/scripts/auteur.py`**

```python
"""Rôle et équipes de la personne connectée, et la propriété où l'inscrire comme auteur."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog, backlog_stockage  # noqa: E402
from web import config  # noqa: E402


def run(args: argparse.Namespace) -> str:
    email = config.agent_user_email()
    if not email:
        return "Personne connectée inconnue : l'auteur ne sera pas inscrit."
    auteur = backlog.trouver_auteur(email)
    if auteur is None:
        return "Absent de l'Annuaire et de Notion : l'auteur ne sera pas inscrit."
    equipes = {e["nom"]: e["id"] for e in backlog_stockage.contexte_courant()["equipes"]}
    noms = {i: n for n, i in equipes.items()}
    lignes = [
        f"Auteur : {auteur.nom}",
        f"Rôles : {', '.join(auteur.roles) or 'inconnus (demander son rôle à la personne)'}",
        f"Équipes : {', '.join(noms.get(i, 'équipe inactive') for i in auteur.equipes) or 'aucune'}",
        f"Compte Notion : {'trouvé' if auteur.notion_id else 'introuvable'}",
    ]
    if args.equipe:
        cibles = [equipes[n] for n in args.equipe if n in equipes]
        lignes.append(f"Inscrit dans : {backlog.champ_auteur(auteur, cibles)}")
    return "\n".join(lignes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equipe", action="append", default=[], help="nom exact de l'équipe destinataire")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
```

- [ ] **Étape 7 : écrire `skills/rediger_ticket/scripts/creer.py`**

```python
"""Crée le ticket dans le Backlog unifié ; sans --go, montre seulement ce qui serait créé."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog, backlog_creation, backlog_stockage  # noqa: E402
from web import config  # noqa: E402


def resoudre(brouillon: dict, contexte: dict, auteur: backlog.Auteur | None) -> backlog_creation.Ticket:
    equipes = {e["nom"]: e for e in contexte["equipes"]}
    inconnues = [n for n in brouillon["equipes"] if n not in equipes]
    if inconnues:
        raise ValueError(f"Équipe inconnue : {', '.join(inconnues)}")
    ids = [equipes[n]["id"] for n in brouillon["equipes"]]
    epic = None
    if brouillon.get("epic"):
        epics = {e["nom"]: e["id"] for n in brouillon["equipes"] for e in equipes[n]["epics"]}
        if brouillon["epic"] not in epics:
            raise ValueError(f"Épic inconnu pour ces équipes : {brouillon['epic']}")
        epic = epics[brouillon["epic"]]
    return backlog_creation.Ticket(
        titre=brouillon["titre"],
        corps=brouillon["corps"],
        equipes=ids,
        statut=brouillon["statut"],
        types=brouillon["types"],
        figma=brouillon.get("figma") or None,
        epic=epic,
        champ_auteur=brouillon.get("champ_auteur") or (backlog.champ_auteur(auteur, ids) if auteur else None),
        auteur_notion_id=auteur.notion_id if auteur else None,
    )


def run(args: argparse.Namespace) -> str:
    brouillon = json.loads(Path(args.brouillon).read_text())
    email = config.agent_user_email()
    ticket = resoudre(brouillon, backlog_stockage.contexte_courant(), backlog.trouver_auteur(email) if email else None)
    proprietes = backlog_creation.construire_proprietes(ticket)
    if not args.go:
        return "Vérification seulement (sans --go) : rien n'est créé.\n" + json.dumps(proprietes, ensure_ascii=False, indent=2)
    _, url = backlog_creation.creer_ticket(ticket)
    return f"Ticket créé : {url}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brouillon", help="fichier JSON du brouillon validé par l'auteur")
    parser.add_argument("--go", action="store_true", help="créer vraiment, après l'accord explicite de l'auteur")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
```

- [ ] **Étape 8 : lancer les tests**

Run: `uv run --frozen pytest tests/test_rediger_ticket_scripts.py -q`
Expected: `17 passed`

Les scripts se lancent depuis la racine du dépôt, comme les autres skills (le répertoire courant de l'agent est la racine).

- [ ] **Étape 9 : committer et attester**

```bash
git add skills/rediger_ticket/scripts tests/test_rediger_ticket_scripts.py
git commit -m "Add command-line scripts for the ticket drafting skill"
make paved-road-advance DOD=DOD-5 CMD='uv run --frozen pytest tests/test_rediger_ticket_scripts.py -k dod_5'
```

---

### Tâche 8 : le skill (`SKILL.md`, exemples, lecture de maquette)

**Fichiers :**
- Créer : `skills/rediger_ticket/SKILL.md`, `skills/rediger_ticket/exemples.md`, `skills/rediger_ticket/maquette.md`

- [ ] **Étape 1 : écrire `skills/rediger_ticket/SKILL.md`**

````markdown
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
5. **Auteur** : `.venv/bin/python skills/rediger_ticket/scripts/auteur.py --equipe "<équipe recommandée>"`. Si ses rôles sont inconnus, demande-lui son rôle (PM, design, dev ou data, autre) et mets le champ correspondant dans le brouillon (`champ_auteur`). Sans compte Notion, dis-lui que le ticket sera créé sans auteur inscrit.
6. **Proposition** (format plus bas). Attends un accord explicite (« go », « crée-le », « ok »). Applique les corrections demandées et remontre si elles sont importantes.
7. **Création** : écris le brouillon dans `/tmp/rediger_ticket/brouillon.json`, lance `.venv/bin/python skills/rediger_ticket/scripts/creer.py /tmp/rediger_ticket/brouillon.json` (vérification), puis la même commande avec `--go`. Donne le lien du ticket.

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

`/tmp/rediger_ticket/brouillon.json` :

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

## Liste de vérification finale

- [ ] Titre : un verbe à l'infinitif et son objet, sans jargon opaque.
- [ ] Ouverture directement sous le titre, commençant par `:autometa:`.
- [ ] Aucune solution de toi ; chaque discussion d'implémentation de l'entrée est dans « Pistes techniques évoquées », attribuée.
- [ ] Chaque texte exact, livrable, lien et question restée ouverte de l'entrée est dans le ticket.
- [ ] Aucun nom de personne, de structure, ni donnée d'exemple de maquette.
- [ ] Équipe, statut, type, épic et champ de l'auteur justifiés ; 3 questions au plus.
````

- [ ] **Étape 2 : écrire `skills/rediger_ticket/exemples.md`**

`````markdown
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
`````

Vérifier qu'il ne contient ni e-mail, ni lien Notion, ni identifiant :

Run: `grep -nE "@|notion\.so|[0-9a-f]{32}" skills/rediger_ticket/exemples.md || echo "propre"`
Expected: `propre`

- [ ] **Étape 3 : écrire `skills/rediger_ticket/maquette.md`**

```markdown
# Lire une maquette Figma

Le script `maquette.py` donne, pour chaque cadre, son nom, ses textes visibles et une image. **Regarde chaque image** avant d'écrire.

## Ce que la maquette apporte

| Dans la maquette | Dans le ticket |
|---|---|
| le nom de l'écran, du parcours, de la page | « Périmètre », avec le nom affiché |
| un texte nouveau ou modifié (titre, message, bouton, lien) que l'entrée ne donne pas | « Attendu », recopié tel quel, avec « (maquette) » |
| plusieurs versions (« Avant / Après », « Version de base / Choix 1 », variantes A et B) | la version cible ; si l'entrée ne dit pas laquelle est retenue, une question dans « À trancher » |
| des états (vide, erreur, selon le profil) | une puce par état |

## Ce qu'elle n'apporte pas

- Les **données d'exemple** (noms, structures, dates, e-mails, montants) : fictives ou personnelles, jamais recopiées.
- Le reste de l'écran : ne décris que ce qui change ou concerne la demande.
- Les détails visuels : l'équipe a la maquette.

## Contrôles

- La maquette correspond-elle à la demande ? Sinon, ne t'en sers pas et demande : « Le lien Figma montre <ce qu'il montre> : est-ce le bon cadre ? »
- Contradiction entre l'entrée et la maquette : l'entrée prime ; signale l'écart dans « À trancher ».
- Lien non lu (sans node-id, accès refusé) : garde le lien et demande un lien vers le cadre.
```

- [ ] **Étape 4 : vérifier que le skill est trouvé et committer**

Run: `ls .claude/skills/rediger_ticket/SKILL.md && head -3 skills/rediger_ticket/SKILL.md`
Expected: le fichier existe (`.claude/skills` pointe vers `skills/`) ; l'en-tête porte `name: rediger_ticket`.

```bash
git add skills/rediger_ticket/SKILL.md skills/rediger_ticket/exemples.md skills/rediger_ticket/maquette.md
git commit -m "Add the ticket drafting skill instructions"
```

---

### Tâche 9 : vérifications d'ensemble

- [ ] **Étape 1 : formatage, tests et lint**

Run: `make format`
Expected: les fichiers créés sont mis au format de ruff (relancer les tests s'il a touché du code).

Run: `make test`
Expected: tout passe.

Run: `make lint`
Expected: aucune erreur (ruff, format, qualité des tests, délais HTTP).

Run: `make security`
Expected: aucun constat nouveau dans `lib/` ni `skills/rediger_ticket/`.

- [ ] **Étape 2 : relire `.claude/rules/`** et vérifier le diff : lecture d'environnement seulement dans `web/config.py`, docstrings d'une ligne, aucun identifiant Notion ni donnée réelle.

Run: `git diff main --stat && git diff main | grep -nE "[0-9a-f]{32}|@inclusion|figd_" || echo "rien de sensible"`
Expected: `rien de sensible`.

- [ ] **Étape 3 : rejouer les preuves périmées**

Run: `make paved-road-reprove`
Expected: toutes les attestations repassent.

- [ ] **Étape 4 : lentille de cohérence** (`paved-road:design-coherence`) sur le diff ; corriger ou justifier chaque bloqueur.

---

### Tâche 10 : configuration des environnements (avec l'utilisateur)

`FIGMA_ACCESS_TOKEN` est déjà posé sur `autometa-staging` et `matometa` (2026-10-30) ; les review apps héritent de `autometa-staging`.

- [ ] **Étape 1 : demander à l'utilisateur** les identifiants des bases « Backlog unifié » et « Annuaire des membres », et son accord pour les poser sur staging.

- [ ] **Étape 2 : poser les variables sur staging**

```bash
scalingo --app autometa-staging env-set NOTION_BACKLOG_DB=<id> NOTION_ANNUAIRE_DB=<id>
```

L'intégration Notion d'autometa lit déjà ces deux bases (vérifié le 2026-10-30). Pour la prod (`matometa`), même commande, au moment de la mise en production, avec l'accord de l'utilisateur.

---

### Tâche 11 : rejouer le banc d'essai (dépôt privé)

Le banc est dans `organisation-produit/exploration/redacteur-tickets/banc/` (26 entrées anonymes et leurs vérités). Il n'entre pas dans autometa.

- [ ] **Étape 1 :** dans le dépôt privé, faire rédiger les 26 entrées par un agent qui suit `skills/rediger_ticket/SKILL.md` (au lieu de `consignes/G-consigne.md`), puis les faire juger contre les sorties de G avec `consignes/grille-G.md` (outils dans `banc/outils/`).
- [ ] **Étape 2 :** vérifier qu'il n'y a pas de recul (rang moyen, fidélité, couverture). Sinon, reprendre l'écart entre G et le SKILL.md avant la PR.

---

### Tâche 12 : smoke sur staging (avec l'utilisateur)

- [ ] **Étape 1 :** sur la review app ou sur staging, dans le chat, coller une entrée du banc avec un lien Figma, et demander un ticket. Vérifier : maquette lue (images regardées), contexte chargé, proposition au bon format, 3 questions au plus, rien de créé.
- [ ] **Étape 2 :** avec l'accord de l'utilisateur, répondre « go » sur un ticket intitulé `[TEST autometa] …` en `Bac à sable 🏝️`. Vérifier dans Notion : propriétés, corps, marqueur, auteur dans le bon champ, et absence de Priorité, Période, Estimation. Puis archiver la page :

```bash
.venv/bin/python -c "from lib import notion; notion.notion_request('PATCH', 'pages/<id>', {'archived': True})"
```

- [ ] **Étape 3 :** `make paved-road-status` ; ouvrir la PR avec la DoD, le journal et les attestations (l'utilisateur pousse et ouvre la PR).
