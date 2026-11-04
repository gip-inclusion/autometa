"""CLI: propose, create after confirmation, retire an agent; deliver its runs and approve its productions."""

import argparse
import json
import sys
from pathlib import Path

import httpx
import yaml

from lib import agents


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    proposer = commands.add_parser("proposer", help="valider et enregistrer une proposition, sans rien créer")
    proposer.add_argument("--config", required=True, type=Path, help="fichier YAML pdi.agent/1")
    proposer.add_argument("--consigne", required=True, type=Path, help="consigne du job, autosuffisante")
    for name in ("creer", "retirer", "voir"):
        commands.add_parser(name).add_argument("proposition")
    livrer = commands.add_parser("livrer", help="livrer la sortie d'un run terminé")
    livrer.add_argument("--agent", required=True)
    livrer.add_argument("--run", required=True)
    for name in ("montrer-envoi", "approuver-envoi"):
        sub = commands.add_parser(name)
        sub.add_argument("--agent", required=True)
        sub.add_argument("--envoi", required=True)
    args = parser.parse_args(argv)

    actions = {
        "proposer": lambda: agents.plan(args.config.read_text(), args.consigne.read_text()),
        "creer": lambda: agents.apply(args.proposition),
        "retirer": lambda: agents.revert(args.proposition),
        "voir": lambda: agents.show(args.proposition),
        "livrer": lambda: agents.deliver_run(args.agent, args.run),
        "montrer-envoi": lambda: agents.present_envoi(args.agent, args.envoi),
        "approuver-envoi": lambda: agents.approve_envoi(args.agent, args.envoi),
    }
    try:
        out = actions[args.command]()
    except (ValueError, PermissionError, yaml.YAMLError, httpx.HTTPError) as exc:
        print(f"refusé : {exc}", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
