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
    commands.add_parser("destinations", help="destinations, modèles, préparations et cadences permis")
    for name, help_text in (
        ("proposer-lancement", "montrer ce qu'un run lancé maintenant ferait, sans rien lancer"),
        ("lancer", "préparations puis run, seulement après confirmation dans un message ultérieur"),
    ):
        commands.add_parser(name, help=help_text).add_argument("--agent", required=True)
    livrer = commands.add_parser("livrer", help="livrer la sortie d'un run terminé")
    livrer.add_argument("--agent", required=True)
    livrer.add_argument("--run", required=True)
    for name in ("montrer-envoi", "approuver-envoi"):
        sub = commands.add_parser(name)
        sub.add_argument("--agent", required=True)
        sub.add_argument("--envoi", required=True)
    files = {
        "fichier": "lire un fichier de l'agent, la dernière version ou --version",
        "historique": "les versions d'un fichier, sans contenu",
        "comparer": "la différence entre deux versions (--de, --a)",
        "proposer-retour": "montrer ce que rendrait un retour à --version, sans rien écrire",
        "revenir": "écrire la version proposée, seulement après confirmation dans un message ultérieur",
    }
    for name, help_text in files.items():
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--agent", required=True)
        sub.add_argument("--nom", required=True)
        if name in ("fichier", "proposer-retour"):
            sub.add_argument("--version", type=int, required=name == "proposer-retour")
        if name == "comparer":
            sub.add_argument("--de", type=int, required=True)
            sub.add_argument("--a", type=int, required=True)
    args = parser.parse_args(argv)

    actions = {
        "proposer": lambda: agents.plan(args.config.read_text(), args.consigne.read_text()),
        "creer": lambda: agents.apply(args.proposition),
        "retirer": lambda: agents.revert(args.proposition),
        "voir": lambda: agents.show(args.proposition),
        "destinations": agents.catalogue,
        "proposer-lancement": lambda: agents.present_launch(args.agent),
        "lancer": lambda: agents.launch(args.agent),
        "livrer": lambda: agents.deliver_run(args.agent, args.run),
        "montrer-envoi": lambda: agents.present_envoi(args.agent, args.envoi),
        "approuver-envoi": lambda: agents.approve_envoi(args.agent, args.envoi),
        "fichier": lambda: agents.read_file(args.agent, args.nom, args.version),
        "historique": lambda: agents.file_history(args.agent, args.nom),
        "comparer": lambda: agents.compare_file(args.agent, args.nom, args.de, args.a),
        "proposer-retour": lambda: agents.present_file_revert(args.agent, args.nom, args.version),
        "revenir": lambda: agents.revert_file(args.agent, args.nom),
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
