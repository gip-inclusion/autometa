"""Sort la ligne de base du paved road en Markdown sur stdout."""

import argparse
import sys

from lib import paved_road


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90, help="fenêtre d'observation en jours")
    args = parser.parse_args(argv)
    print(paved_road.render(paved_road.collect(args.days)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
