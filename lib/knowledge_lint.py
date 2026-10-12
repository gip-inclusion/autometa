"""Cohérence des connaissances de l'agent : chaque fiche se vérifie contre le dépôt, les registres et le catalogue."""

import ast
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

REGISTRY_DOC = "AGENT.md"
REGISTRY_HEADING = "Sites web"
# Why: la règle de priorité entre sources vit dans les consignes de prod (injectées verbatim), celle
# du choix des tables dans le skill de la base centrale ; une copie ailleurs finit toujours par diverger.
AUTHORITATIVE_SECTIONS = (
    ("AGENT.md", "Sources de données"),
    ("skills/autometa_tables_db/SKILL.md", "Règles de sélection des tables"),
)
DATABASE_SOURCES = ("autometa_tables_db", "data_inclusion", "dora_staging", "appli_monrecap", "appli_monrecap_db")
STALE_AFTER_DAYS = 180

FENCE = re.compile(r"^```(\w*)\s*$")
HEADING = re.compile(r"^(#+)\s+(.*?)\s*$")
REPO_PATH = re.compile(
    r"`((?:knowledge|skills|lib|web|scripts|docs|config|cron|tests|plugins)/[^`\s*<>{}]+?)(?::\d+)?`"
)
LINK = re.compile(r"\]\((?!https?:|#|mailto:)([^)\s#]+)")
IMPORT = re.compile(r"\bfrom\s+((?:lib|web)(?:\.\w+)+)\s+import\s+\(?([\w\s,]+)")
METABASE_INSTANCE = re.compile(r"(?:get_metabase\(\s*|metabase\w*\([^)]*?\binstance\s*=\s*)[\"'](\w+)[\"']")
TABLE_REF = re.compile(
    r"\b(?:from|join)\s+((?:\"[^\"]+\"|\w+)(?:\.(?:\"[^\"]+\"|\w+))?)(?![\w.\"])(?!\s*\()(?:\s+(?:as\s+)?(\w+))?", re.I
)
CTE = re.compile(r"(?:\bwith|,)\s+(\w+)\s+as\s*\(", re.I)
EXTRACT_CALL = re.compile(r"\b(?:extract|substring|trim)\s*\([^)]*\)", re.I)
COLUMN_REF = re.compile(r"\b(\w+)\.(\"[^\"]+\"|\w+)")
BACKTICK = re.compile(r"`([^`]+)`")
SQL_KEYWORDS = {
    "where", "join", "on", "left", "right", "inner", "outer", "full", "cross", "natural", "group", "order",
    "limit", "using", "lateral", "union", "having", "as", "and", "or", "select", "set", "window", "offset",
}  # fmt: skip


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} — {self.message}"


@dataclass(frozen=True)
class Site:
    names: tuple[str, ...]
    url: str
    matomo_id: int


def documents(root: Path) -> list[Path]:
    """Ce que l'agent lit comme consigne ou connaissance."""
    skills = [p for p in sorted(root.glob("skills/*/SKILL.md")) if p.parent.name != "pdf"]
    return (
        [root / name for name in ("AGENT.md", "CLAUDE.md") if (root / name).is_file()] + skills + knowledge_files(root)
    )


def knowledge_files(root: Path) -> list[Path]:
    return sorted((root / "knowledge").rglob("*.md"))


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def front_matter(text: str) -> dict | None:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return None
    try:
        parsed = yaml.safe_load(text[4 : text.index("\n---\n", 4)])
    except yaml.YAMLError:
        return None
    return parsed if isinstance(parsed, dict) else None


def prose_lines(text: str) -> list[tuple[int, str]]:
    """Lignes hors blocs de code, numérotées."""
    out, fenced = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            out.append((number, line))
    return out


def code_blocks(text: str) -> list[tuple[str, int, str]]:
    blocks, current, language, start = [], None, "", 0
    for number, line in enumerate(text.splitlines(), 1):
        fence = FENCE.match(line)
        if fence and current is None:
            current, language, start = [], fence.group(1).lower(), number + 1
        elif fence:
            blocks.append((language, start, "\n".join(current)))
            current = None
        elif current is not None:
            current.append(line)
    return blocks


def section(text: str, title: str) -> list[tuple[int, str]]:
    """Lignes d'une section, jusqu'au titre suivant de niveau égal ou supérieur."""
    out, level = [], None
    for number, line in prose_lines(text):
        heading = HEADING.match(line)
        if heading and level is not None and len(heading.group(1)) <= level:
            break
        if level is not None:
            out.append((number, line))
        elif heading and heading.group(2) == title:
            level = len(heading.group(1))
    return out


def table_rows(lines: list[tuple[int, str]]) -> list[tuple[int, dict[str, str]]]:
    """Lignes de tableaux markdown, chacune indexée par l'en-tête de son tableau."""
    rows, header = [], None
    for number, line in lines:
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
        elif not all(set(cell) <= set("-: ") for cell in cells):
            rows.append((number, dict(zip(header, cells))))
    return rows


def plain(cell: str) -> str:
    return re.sub(r"[`*]", "", cell).strip()


def sites(root: Path) -> list[Site]:
    """Le tableau des sites des consignes : seule référence pour nom, adresse et numéro Matomo."""
    text = (root / REGISTRY_DOC).read_text()
    out = []
    for _, row in table_rows(section(text, REGISTRY_HEADING)):
        name = plain(row["Site"])
        names = tuple(part.strip() for part in re.split(r"\(ex-|\)", name) if part.strip())
        out.append(Site(names=names, url=plain(row["URL"]), matomo_id=int(plain(row["ID Matomo"]))))
    return out


def sources_config(root: Path) -> dict:
    return yaml.safe_load((root / "config" / "sources.yaml").read_text())


def known_sources(root: Path) -> set[str]:
    config = sources_config(root)
    instances = {f"metabase:{name}" for name in config["metabase"] if not name.startswith("_")}
    matomo = {f"matomo:{site.matomo_id}" for site in sites(root)}
    skills = {path.parent.name for path in root.glob("skills/*/SKILL.md")}
    return {"aucune", "matomo"} | (set(config) - {"tag_manager"}) | instances | matomo | skills


def module_symbols(root: Path, module: str) -> set[str] | None:
    base = root / Path(*module.split("."))
    path = base.with_suffix(".py") if base.with_suffix(".py").is_file() else base / "__init__.py"
    if not path.is_file():
        return None
    names = {p.stem for p in base.glob("*.py")} if base.is_dir() else set()
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names |= {(alias.asname or alias.name).split(".")[0] for alias in node.names}
    return names


def dead_references(root: Path) -> list[Finding]:
    """Fichiers, modules et fonctions du dépôt cités mais introuvables."""
    findings = []
    for doc in documents(root):
        text, shown = doc.read_text(), rel(root, doc)
        for number, line in prose_lines(text):
            for cited in REPO_PATH.findall(line):
                if not (root / cited.rstrip("/")).exists():
                    findings.append(Finding(shown, number, f"chemin introuvable : {cited}"))
            for cited in LINK.findall(line):
                if not (doc.parent / cited).exists():
                    findings.append(Finding(shown, number, f"lien introuvable : {cited}"))
        for number, line in enumerate(text.splitlines(), 1):
            for module, imported in IMPORT.findall(line):
                symbols = module_symbols(root, module)
                if symbols is None:
                    findings.append(Finding(shown, number, f"module introuvable : {module}"))
                    continue
                for name in (part.split()[0] for part in imported.split(",") if part.strip()):
                    if name not in symbols:
                        findings.append(Finding(shown, number, f"{module} ne définit pas {name}"))
    return findings


def site_conflicts(root: Path) -> list[Finding]:
    """Un site nommé, numéroté ou rattaché à un conteneur autrement que dans le tableau des sites."""
    registry = sites(root)
    by_name = {name.lower(): site for site in registry for name in site.names}
    by_id = {site.matomo_id: site for site in registry}
    tag_manager = sources_config(root).get("tag_manager", {}).get("sites", [])
    containers = {entry["matomo_id"]: entry["container_id"] for entry in tag_manager}
    findings = []
    for entry in tag_manager:
        site = by_id.get(entry["matomo_id"])
        owner = by_name.get(entry["name"].lower())
        if site and owner and owner is not site:
            findings.append(
                Finding("config/sources.yaml", 0, f"« {entry['name']} » porte le site {entry['matomo_id']}, "
                        f"le tableau des sites lui donne le {owner.matomo_id}")
            )  # fmt: skip
    for doc in documents(root):
        text, shown = doc.read_text(), rel(root, doc)
        lines = prose_lines(text)
        registry_lines = {n for n, _ in section(text, REGISTRY_HEADING)} if shown == REGISTRY_DOC else set()
        for number, row in table_rows(lines):
            if number in registry_lines:
                continue
            findings += row_conflicts(shown, number, row, by_name, by_id, containers)
        for number, line in lines:
            for name, site in by_name.items():
                for inside in re.findall(rf"\b{re.escape(name)}\s*\(([^)]*)\)", line, re.I):
                    other = cited_site(inside, registry)
                    if other and other is not site:
                        findings.append(Finding(shown, number, f"« {name} » associé à {inside.strip()}, "
                                                f"qui désigne {other.names[0]} ({other.matomo_id})"))  # fmt: skip
            findings += [
                Finding(shown, number, f"adresse {stale} pour {site.names[0]}, le tableau des sites dit {site.url}")
                for site in registry
                if (stale := other_host(site.url))
                and re.search(rf"(?<![\w.-]){re.escape(stale)}(?![\w-])", without_code(line))
            ]
    return findings


def other_host(url: str) -> str | None:
    """L'autre forme, avec ou sans `beta.`, d'une adresse en .gouv.fr — celle que le tableau ne retient pas."""
    if not url.endswith(".gouv.fr"):
        return None
    return url.replace(".beta.gouv.fr", ".gouv.fr") if ".beta." in url else url.replace(".gouv.fr", ".beta.gouv.fr")


def without_code(line: str) -> str:
    """Le code en ligne cite des données (définitions de segments, motifs) : seule la prose affirme."""
    return re.sub(r"`[^`]*`", "", line)


def cited_site(text: str, registry: list[Site]) -> Site | None:
    for site in registry:
        if re.search(rf"(?<![\d.]){site.matomo_id}(?!\d)", text) or re.search(
            rf"(?<![\w.-]){re.escape(site.url)}(?![\w-])", text
        ):
            return site
    return None


def row_conflicts(shown, number, row, by_name, by_id, containers) -> list[Finding]:
    name_col = next((c for c in row if c.lower() in ("site", "nom", "name")), None)
    id_col = next((c for c in row if re.search(r"\bid\b|idsite", c, re.I)), None)
    if not name_col or not id_col or not plain(row[id_col]).isdigit():
        return []
    matomo_id, name = int(plain(row[id_col])), plain(row[name_col]).lower()
    findings = []
    owner = by_name.get(name)
    if owner and matomo_id in by_id and owner.matomo_id != matomo_id:
        findings.append(Finding(shown, number, f"« {plain(row[name_col])} » associé au site {matomo_id}, "
                                f"le tableau des sites lui donne le {owner.matomo_id}"))  # fmt: skip
    container_col = next((c for c in row if re.search(r"conteneur|container", c, re.I)), None)
    expected = containers.get(matomo_id)
    if container_col and expected and plain(row[container_col]) != expected:
        findings.append(Finding(shown, number, f"conteneur {plain(row[container_col])} pour le site {matomo_id}, "
                                f"config/sources.yaml dit {expected}"))  # fmt: skip
    return findings


def unknown_metabase_instances(root: Path) -> list[Finding]:
    instances = set(sources_config(root)["metabase"])
    return [
        Finding(
            rel(root, doc), text.count("\n", 0, match.start()) + 1, f"instance Metabase inconnue : {match.group(1)}"
        )
        for doc in documents(root)
        for text in [doc.read_text()]
        for match in METABASE_INSTANCE.finditer(text)
        if match.group(1) not in instances
    ]


def declared_sources(meta: dict | None) -> list[str]:
    value = (meta or {}).get("source")
    return [value] if isinstance(value, str) else list(value or [])


def front_matter_problems(root: Path) -> list[Finding]:
    """Chaque fiche dit quelle source elle décrit et quand elle a été vérifiée."""
    known, findings = known_sources(root), []
    for doc in knowledge_files(root):
        meta, shown = front_matter(doc.read_text()), rel(root, doc)
        if not declared_sources(meta):
            findings.append(Finding(shown, 1, "en-tête absent : « source » (la source décrite) est requis"))
        findings += [Finding(shown, 1, f"source inconnue : {s}") for s in declared_sources(meta) if s not in known]
        if not isinstance((meta or {}).get("verifie_le"), date):
            findings.append(Finding(shown, 1, "en-tête absent : « verifie_le » (AAAA-MM-JJ) est requis"))
    return findings


def stale_documents(root: Path, today: date) -> list[Finding]:
    """Fiches dont la dernière vérification date de plus de six mois — signalées, jamais bloquantes."""
    findings = []
    for doc in knowledge_files(root):
        checked = (front_matter(doc.read_text()) or {}).get("verifie_le")
        if isinstance(checked, date) and (today - checked).days > STALE_AFTER_DAYS:
            findings.append(
                Finding(rel(root, doc), 1, f"vérifiée le {checked}, il y a plus de {STALE_AFTER_DAYS} jours")
            )
    return findings


def words(text: str) -> set[str]:
    return set(re.findall(r"\w+", plain(text).lower()))


def sentences(lines: list[tuple[int, str]]) -> list[tuple[int, set[str]]]:
    return [
        (number, words(sentence))
        for number, line in lines
        for sentence in re.split(r"(?<=[.;:])\s+|\s+[—→]\s+", line)
        # Why: sous huit mots, une phrase (« Priorité absolue sur Metabase. ») se retrouve légitimement partout.
        if len(words(sentence)) >= 8
    ]


def copied_rules(root: Path) -> list[Finding]:
    """Une règle normative recopiée hors de son unique emplacement."""
    findings = []
    for owner, title in AUTHORITATIVE_SECTIONS:
        rules = sentences(section((root / owner).read_text(), title))
        for doc in documents(root):
            if rel(root, doc) == owner:
                continue
            for number, candidate in sentences(prose_lines(doc.read_text())):
                for rule_line, rule in rules:
                    # Why: 0,8 de recouvrement des mots attrape une copie retouchée, pas un renvoi qui cite la règle.
                    if len(candidate & rule) / len(candidate | rule) >= 0.8:
                        findings.append(Finding(rel(root, doc), number, f"recopie la règle de {owner}:{rule_line}, "
                                                f"qui doit rester seule — y renvoyer"))  # fmt: skip
                        break
    return findings


def refuted_claims(root: Path) -> list[Finding]:
    """Une affirmation reconnue fausse ne revient pas dans une fiche."""
    path = root / "knowledge" / "refutations.yaml"
    if not path.is_file():
        return []
    entries = yaml.safe_load(path.read_text())
    return [
        Finding(rel(root, doc), number, f"affirmation réfutée « {entry['motif']} » : {entry['raison']}")
        for doc in documents(root)
        for number, line in enumerate(doc.read_text().splitlines(), 1)
        for entry in entries
        if re.search(entry["motif"], line, re.I)
    ]


def catalog_path(root: Path, source: str) -> Path:
    return root / "knowledge" / "catalog" / f"{source.replace(':', '_')}.json"


def is_database(source: str) -> bool:
    return source in DATABASE_SOURCES or source.startswith("metabase:")


def doc_sources(root: Path, doc: Path) -> list[str]:
    meta = front_matter(doc.read_text())
    if doc.name == "SKILL.md":
        return [meta["name"]] if meta and meta.get("name") in DATABASE_SOURCES else []
    return declared_sources(meta)


def uncatalogued(root: Path) -> list[Finding]:
    """Fiches dont les tables ne sont pas vérifiées faute d'instantané du catalogue de leur source."""
    return [
        Finding(rel(root, doc), 1, f"tables non vérifiées : aucun instantané {rel(root, catalog_path(root, s))}")
        for doc in documents(root)
        for s in doc_sources(root, doc)
        if is_database(s) and not catalog_path(root, s).is_file()
    ]


def identifier(raw: str) -> str:
    return raw[1:-1] if raw.startswith('"') else raw.lower()


def lookup(catalog: dict[str, list[str]], reference: str) -> list[str] | None:
    """Colonnes d'une table du catalogue, qualifiée ou non ; None si elle n'existe nulle part."""
    parts = [identifier(p) for p in re.findall(r"\"[^\"]+\"|\w+", reference)]
    if len(parts) == 2:
        return catalog.get(".".join(parts))
    matches = [columns for key, columns in catalog.items() if key.split(".", 1)[1] == parts[0]]
    return [c for columns in matches for c in columns] if matches else None


def sql_problems(block: str, catalog: dict[str, list[str]]) -> list[tuple[int, str]]:
    block = EXTRACT_CALL.sub("", block)
    ctes = {name.lower() for name in CTE.findall(block)}
    problems, aliases = [], {}
    for match in TABLE_REF.finditer(block):
        reference, alias = match.group(1), match.group(2)
        line = block.count("\n", 0, match.start())
        if identifier(reference) in ctes or re.search(r"[<>{}]", reference):
            continue
        columns = lookup(catalog, reference)
        if columns is None:
            problems.append((line, f"table absente du catalogue : {reference}"))
            continue
        aliases[reference.split(".")[-1].strip('"').lower()] = columns
        if alias and alias.lower() not in SQL_KEYWORDS:
            aliases[alias.lower()] = columns
    for match in COLUMN_REF.finditer(block):
        columns = aliases.get(match.group(1).lower())
        if columns is not None and identifier(match.group(2)) not in columns:
            line = block.count("\n", 0, match.start())
            problems.append((line, f"colonne absente du catalogue : {match.group(0)}"))
    return problems


def load_catalog(root: Path, sources: list[str]) -> dict[str, list[str]] | None:
    """Union des catalogues des sources de bases d'une fiche ; None si l'un d'eux manque."""
    databases = [s for s in sources if is_database(s)]
    if not databases or not all(catalog_path(root, s).is_file() for s in databases):
        return None
    return {k: v for s in databases for k, v in json.loads(catalog_path(root, s).read_text())["tables"].items()}


def catalog_problems(root: Path) -> list[Finding]:
    """Tables et colonnes citées absentes de l'instantané du catalogue de la source de la fiche."""
    findings = []
    for doc in documents(root):
        catalog = load_catalog(root, doc_sources(root, doc))
        if catalog is None:
            continue
        text, shown = doc.read_text(), rel(root, doc)
        for language, start, block in code_blocks(text):
            if language == "sql":
                findings += [
                    Finding(shown, start + offset, message) for offset, message in sql_problems(block, catalog)
                ]
        for number, line in section(text, "Tables de référence"):
            for name in BACKTICK.findall(line):
                if re.fullmatch(r"[\w.\"]+", name) and lookup(catalog, name) is None:
                    findings.append(Finding(shown, number, f"table de référence absente du catalogue : {name}"))
    return findings


def findings(root: Path) -> list[Finding]:
    """Tout ce qui rend deux consignes contradictoires ou une consigne fausse — bloquant."""
    return (
        dead_references(root)
        + site_conflicts(root)
        + unknown_metabase_instances(root)
        + front_matter_problems(root)
        + copied_rules(root)
        + refuted_claims(root)
        + catalog_problems(root)
    )
