"""CLI pour explorer le catalogue RPE et lancer des requêtes à la demande."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.rpe import RpeClient, doctor  # noqa: E402


def parse_dim(spec: str):
    if ":" in spec:
        dim, lpos = spec.split(":", 1)
        return {"dim": dim, "hPos": 0, "lPos": int(lpos)}
    return spec


def grep(items: list, term: str) -> list:
    if not term:
        return items
    t = term.lower()
    return [
        i for i in items if t in str(i.get("id", "")).lower() or t in str(i.get("label") or i.get("name") or "").lower()
    ]


def parse_ddvar(v: str):
    """Valeur de bascule : entier si numérique (cas Switch=0), sinon chaîne brute."""
    return int(v) if v.lstrip("-").isdigit() else v


TIER_ALIASES = {
    "region": "Région",
    "région": "Région",
    "reg": "Région",
    "dept": "Département",
    "dep": "Département",
    "departement": "Département",
    "département": "Département",
    "cle": "CLPE",
    "clpe": "CLPE",
}


def parse_territory(specs: list):
    """[CODE:PALIER, …] → (palier canonique, [codes]) pour le filtre géo serveur ; un seul palier à la fois."""
    if not specs:
        return None
    paliers, codes = set(), []
    for s in specs:
        code, sep, tier = s.partition(":")
        palier = TIER_ALIASES.get(tier.lower()) if sep else None
        if not palier:
            raise SystemExit(f"--territory attend CODE:PALIER (région|département|cle), ex. 78:dept — reçu {s!r}")
        paliers.add(palier)
        codes.append(code)
    if len(paliers) > 1:
        raise SystemExit("--territory : un seul palier à la fois")
    return next(iter(paliers)), codes


def apply_where(rows: list, wheres: list) -> list:
    """Filtre côté client : garde les lignes où row[col] == valeur (ET entre clauses)."""
    for clause in wheres:
        col, _, val = clause.partition("=")
        rows = [r for r in rows if str(r.get(col)) == val]
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Requêter le tableau de bord RPE (DigDash).")
    ap.add_argument("--doctor", action="store_true", help="diagnostic santé RPE (fraîcheur signatures + canari live)")
    ap.add_argument("--list", action="store_true", help="lister les datasets")
    ap.add_argument("--measures", metavar="DATASET", help="lister les mesures d'un dataset")
    ap.add_argument("--grep", metavar="TERME", help="filtrer --measures/--dims par sous-chaîne (id ou label)")
    ap.add_argument("--dims", metavar="DATASET", help="lister les dimensions d'un dataset")
    ap.add_argument("--query", metavar="DATASET", help="dataset à requêter")
    ap.add_argument("--dim", action="append", default=[], help="dimension de ventilation (id ou id:lPos), répétable")
    ap.add_argument(
        "--month",
        metavar="DIM",
        help="série temporelle : ventiler par mois sur cette dim date (lève le filtre de période)",
    )
    ap.add_argument("--measure", action="append", default=[], help="measure_id exact, répétable (défaut: toutes)")
    ap.add_argument(
        "--ddvar",
        action="append",
        default=[],
        help="variable de bascule name=valeur (ex. Switch=0 pour mensuel vs cumul sur une mesure '(switch)'), répétable",
    )
    ap.add_argument(
        "--territory",
        action="append",
        default=[],
        metavar="CODE:PALIER",
        help="filtre géo serveur au bon niveau (ex. 78:dept, 11:region, CLPE78001:cle), répétable. "
        "Pour les cubes lourds (ventilation géo complète injoignable), préférer ceci au --where.",
    )
    ap.add_argument(
        "--where",
        action="append",
        default=[],
        help="filtre côté client sur une colonne du résultat (ex. Région_code=11), répétable.",
    )
    args = ap.parse_args()

    if args.doctor:
        print(json.dumps(doctor(), ensure_ascii=False, indent=1))
        return

    client = RpeClient.connect()
    try:
        if args.list:
            print(json.dumps(client.datasets(), ensure_ascii=False, indent=1))
        elif args.measures:
            print(json.dumps(grep(client.measures(args.measures), args.grep), ensure_ascii=False, indent=1))
        elif args.dims:
            print(json.dumps(grep(client.dimensions(args.dims), args.grep), ensure_ascii=False, indent=1))
        elif args.query:
            dims = [parse_dim(d) for d in args.dim]
            filters = None
            if args.month:  # série temporelle : ventiler par mois + lever le filtre de période figé du template
                dims.append({"dim": args.month, "hPos": 0, "lPos": 0, "format": {"id": "Mois Annee"}})
                filters = {}
            ddvars = {k: parse_ddvar(v) for k, _, v in (d.partition("=") for d in args.ddvar)} or None
            rows = client.query(
                args.query,
                dimensions=dims,
                measures=args.measure or None,
                filters=filters,
                territory=parse_territory(args.territory),
                ddvars=ddvars,
            )
            print(json.dumps(apply_where(rows, args.where), ensure_ascii=False, indent=1))
        else:
            ap.print_help()
    finally:
        client.close()


if __name__ == "__main__":
    main()
