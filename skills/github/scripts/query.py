"""CLI lecture seule des dépôts publics GitHub de gip-inclusion, betagouv, numerique-gouv et suitenumerique."""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import github  # noqa: E402


def clip(lines: list[str], max_lines: int) -> str:
    """Les `max_lines` premières lignes, avec le nombre de lignes coupées."""
    cut = len(lines) - max_lines
    return "\n".join(lines[:max_lines] + ([f"… {cut} lignes coupées"] if cut > 0 else []))


def blame_text(rows: list[dict]) -> list[str]:
    """Les lignes regroupées sous le commit qui les a écrites en dernier."""
    out, previous = [], None
    for row in rows:
        if row["commit"] != previous:
            out.append(f"{row['commit']} {row['date']} {row['author']} — {row['summary']}")
            previous = row["commit"]
        out.append(f"  {row['line']:>5} | {row['text']}")
    return out


def run(args) -> str:
    if args.command == "cleanup":
        shutil.rmtree(github.workspace(), ignore_errors=True)
        return f"supprimé : {github.workspace()}"
    if args.command == "repo":
        meta = github.public(github.repository(args.repo))
        keys = ("full_name", "default_branch", "description", "archived", "pushed_at", "html_url")
        return json.dumps({key: meta[key] for key in keys}, ensure_ascii=False, indent=1)
    if args.command == "read":
        return github.read(args.repo, args.path, args.ref)
    if args.command == "prs":
        return json.dumps(github.pulls(args.repo, args.state, args.commit, args.max), ensure_ascii=False, indent=1)
    if args.command == "pr":
        return json.dumps(github.pull(args.repo, args.number), ensure_ascii=False, indent=1)
    if args.command == "log":
        commits = github.log(args.repo, args.path, args.ref, args.since, args.max)
        return "\n".join(f"{c['commit']} {c['date']} {c['author']} — {c['subject']}" for c in commits)
    if args.command == "blame":
        rows = github.blame(args.repo, args.path, args.ref)
        if args.lines:
            first, last = map(int, args.lines.split(","))
            rows = [row for row in rows if first <= row["line"] <= last]
        return clip(blame_text(rows), args.max_lines)
    if args.command == "show":
        found = github.show(args.repo, args.commit, args.path)
        lines = [f"{found['commit']} — {found['author']}, {found['date']}", "", *found["message"].splitlines()]
        for f in found["files"]:
            lines += ["", f"--- {f['filename']} ({f['status']}, +{f['additions']} −{f['deletions']})"]
            lines += (f["patch"] or "(diff non fourni par GitHub : fichier binaire ou trop gros)").splitlines()
        return clip(lines, args.max_lines)

    github.sweep()
    path, commit = github.clone(args.repo, github.workspace(), args.ref)
    if args.command == "clone":
        return f"{path}\ncommit {commit}"
    found = github.grep(path, args.pattern, args.glob, args.ignore_case, args.max)
    lines = [f"commit {commit} — {found['total']} lignes trouvées"]
    return "\n".join(lines + [f"{m['path']}:{m['line']}: {m['text']}" for m in found["matches"]])


def main() -> None:
    ap = argparse.ArgumentParser(description="Lire les dépôts publics GitHub (lecture seule).")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("cleanup", help="supprimer les clones de la conversation")
    commands = {
        "repo": "métadonnées, dont la branche par défaut",
        "read": "lire un fichier par l'API",
        "prs": "lister les pull requests",
        "pr": "une pull request et ses fichiers",
        "clone": "copie superficielle, à explorer avec les outils de lecture et de recherche",
        "grep": "chercher une expression régulière dans tout le dépôt",
        "log": "historique des commits",
        "blame": "dernier commit de chaque ligne",
        "show": "message et diff d'un commit",
    }
    parsers = {name: sub.add_parser(name, help=text) for name, text in commands.items()}
    for name, parser in parsers.items():
        parser.add_argument("repo", help="org/dépôt, par exemple gip-inclusion/les-emplois")
        if name not in ("repo", "prs", "pr", "show"):
            parser.add_argument("--ref", help="branche, étiquette ou SHA complet (défaut : branche par défaut)")
    parsers["read"].add_argument("path")
    parsers["prs"].add_argument("--state", choices=["open", "closed", "all"], default="open")
    parsers["prs"].add_argument("--commit", help="les pull requests qui contiennent ce commit")
    parsers["prs"].add_argument("--max", type=int, default=30)
    parsers["pr"].add_argument("number", type=int)
    parsers["grep"].add_argument("pattern", help="expression régulière étendue")
    parsers["grep"].add_argument("--glob", help="limiter aux chemins correspondants, par exemple '*.py'")
    parsers["grep"].add_argument("-i", "--ignore-case", action="store_true")
    parsers["grep"].add_argument("--max", type=int, default=200)
    parsers["log"].add_argument("path", nargs="?", help="un fichier ou un dossier")
    parsers["log"].add_argument("--since", help="date, par exemple 2026-01-01")
    parsers["log"].add_argument("--max", type=int, default=30)
    parsers["blame"].add_argument("path")
    parsers["blame"].add_argument("-L", "--lines", help="plage de lignes, par exemple 120,160")
    parsers["show"].add_argument("commit")
    parsers["show"].add_argument("path", nargs="?", help="limiter aux fichiers sous ce chemin")
    for name in ("blame", "show"):
        parsers[name].add_argument("--max-lines", type=int, default=400)

    try:
        print(run(ap.parse_args()))
    except (github.GitHubError, ValueError) as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
