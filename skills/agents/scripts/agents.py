"""CLI: propose, create after confirmation, retire an agent; deliver its runs and approve its deliveries."""

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
    propose = commands.add_parser("propose", help="valider et enregistrer une proposition, sans rien créer")
    propose.add_argument("--config", required=True, type=Path, help="fichier YAML pdi.agent/1")
    propose.add_argument("--instructions", required=True, type=Path, help="consigne du job, autosuffisante")
    propose.add_argument(
        "--file",
        action="append",
        type=Path,
        default=[],
        help="valeur initiale d'un fichier déclaré, nommé comme lui ; écrite à la création si le fichier est vide",
    )
    for name, help_text in (
        ("create", "créer ou modifier l'agent, seulement après confirmation dans un message ultérieur"),
        ("propose-retire", "montrer ce que retirer cette proposition déferait, sans rien retirer"),
        ("retire", "retirer, seulement après confirmation dans un message ultérieur"),
        ("show", "voir une proposition"),
    ):
        commands.add_parser(name, help=help_text).add_argument("changeset")
    commands.add_parser("destinations", help="destinations, modèles, préparations et cadences permis")
    for name, help_text in (
        ("propose-launch", "montrer ce qu'un run lancé maintenant ferait, sans rien lancer"),
        ("launch", "préparations puis run, seulement après confirmation dans un message ultérieur"),
    ):
        commands.add_parser(name, help=help_text).add_argument("--agent", required=True)
    deliver = commands.add_parser("deliver", help="livrer la sortie d'un run terminé")
    deliver.add_argument("--agent", required=True)
    deliver.add_argument("--run", required=True)
    for name in ("show-delivery", "approve-delivery"):
        sub = commands.add_parser(name)
        sub.add_argument("--agent", required=True)
        sub.add_argument("--delivery", required=True)
    files = {
        "file": "lire un fichier de l'agent, la dernière version ou --version",
        "history": "les versions d'un fichier, sans contenu",
        "diff": "la différence entre deux versions (--old, --new)",
        "propose-revert": "montrer ce que rendrait un retour à --version, sans rien écrire",
        "revert": "écrire la version proposée, seulement après confirmation dans un message ultérieur",
    }
    for name, help_text in files.items():
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--agent", required=True)
        sub.add_argument("--name", required=True)
        if name in ("file", "propose-revert"):
            sub.add_argument("--version", type=int, required=name == "propose-revert")
        if name == "diff":
            sub.add_argument("--old", type=int, required=True)
            sub.add_argument("--new", type=int, required=True)
    args = parser.parse_args(argv)

    actions = {
        "propose": lambda: agents.plan(
            args.config.read_text(), args.instructions.read_text(), {f.name: f.read_text() for f in args.file}
        ),
        "create": lambda: agents.apply(args.changeset),
        "propose-retire": lambda: agents.present_retire(args.changeset),
        "retire": lambda: agents.revert(args.changeset),
        "show": lambda: agents.show(args.changeset),
        "destinations": agents.catalogue,
        "propose-launch": lambda: agents.present_launch(args.agent),
        "launch": lambda: agents.launch(args.agent),
        "deliver": lambda: agents.deliver_run(args.agent, args.run),
        "show-delivery": lambda: agents.present_delivery(args.agent, args.delivery),
        "approve-delivery": lambda: agents.approve_delivery(args.agent, args.delivery),
        "file": lambda: agents.read_file(args.agent, args.name, args.version),
        "history": lambda: agents.file_history(args.agent, args.name),
        "diff": lambda: agents.compare_file(args.agent, args.name, args.old, args.new),
        "propose-revert": lambda: agents.present_file_revert(args.agent, args.name, args.version),
        "revert": lambda: agents.revert_file(args.agent, args.name),
    }
    try:
        out = actions[args.command]()
    except (ValueError, PermissionError, RuntimeError, yaml.YAMLError, httpx.HTTPError) as exc:
        print(f"refusé : {exc}", file=sys.stderr)
        return 1
    print(out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
