"""Vocabulaire de tags actif, par facette, avec le nombre de termes attendu."""

from lib.taxonomy import build_prompt_taxonomy, load_vocabulary
from web.db import get_db


def main() -> None:
    with get_db() as session:
        print(build_prompt_taxonomy(load_vocabulary(session)))


if __name__ == "__main__":
    main()
