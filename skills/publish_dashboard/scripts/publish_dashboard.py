"""Publish dashboard skill — thin wrapper over web.publications."""

import argparse
import json
import sys

from web import config, publications


def _serialize(pub: dict) -> dict:
    if pub.get("published_at") is not None:
        pub["published_at"] = pub["published_at"].isoformat()
    return pub


def cmd_publish(args: argparse.Namespace) -> int:
    user = config.agent_user_email()
    if not user:
        print("AUTOMETA_USER_EMAIL not set", file=sys.stderr)
        return 2
    try:
        pub = publications.publish(args.slug, args.env, user)
    except publications.PublicationBlocked as exc:
        print(json.dumps({"error": "publication_blocked", "reason": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(_serialize(pub), indent=2, ensure_ascii=False))
    return 0


def cmd_unpublish(args: argparse.Namespace) -> int:
    ok = publications.unpublish(args.publication_id)
    if not ok:
        print(json.dumps({"error": "not_found", "publication_id": args.publication_id}), file=sys.stderr)
        return 1
    print(json.dumps({"unpublished": args.publication_id}))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    rows = publications.list_publications(args.slug, active_only=not args.all)
    print(json.dumps([_serialize(r) for r in rows], indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish, unpublish, or list dashboard publications.")
    sub = parser.add_subparsers(dest="action", required=True)

    p = sub.add_parser("publish", help="Publish a dashboard to staging or production")
    p.add_argument("--slug", required=True)
    p.add_argument("--env", choices=["staging", "production"], required=True)
    p.set_defaults(func=cmd_publish)

    u = sub.add_parser("unpublish", help="Unpublish a dashboard by publication_id")
    u.add_argument("--publication-id", required=True)
    u.set_defaults(func=cmd_unpublish)

    lst = sub.add_parser("list", help="List a dashboard's publications")
    lst.add_argument("--slug", required=True)
    lst.add_argument("--all", action="store_true", help="Include unpublished rows (audit)")
    lst.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
