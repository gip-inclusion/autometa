"""Réconcilie les review apps Scalingo avec le cycle de vie des pull requests GitHub."""

import argparse
import json
import sys

import httpx

AUTH_URL = "https://auth.scalingo.com/v1/tokens/exchange"
API_URL = "https://api.osc-fr1.scalingo.com/v1"
TIMEOUT = 30.0


def exchange_token(client, api_token):
    """Échange un token API Scalingo contre un bearer JWT de courte durée."""
    response = client.post(AUTH_URL, auth=("", api_token), timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["token"]


def find_review_app(client, bearer, parent_app, pr_number):
    """La review app rattachée à cette PR, ou None."""
    response = client.get(
        f"{API_URL}/apps/{parent_app}/scm_repo_link/review_apps",
        headers={"Authorization": f"Bearer {bearer}"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    for entry in response.json()["review_apps"]:
        pull_request = entry.get("pull_request")
        if pull_request and pull_request["number"] == pr_number:
            return entry
    return None


def app_url(app_name):
    return f"https://{app_name}.osc-fr1.scalingo.io"


def deploy_review_app(client, bearer, parent_app, pr_number):
    """Déclenche la création ou le redéploiement, et renvoie le corps de réponse de Scalingo."""
    response = client.post(
        f"{API_URL}/apps/{parent_app}/scm_repo_link/manual_review_app",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"pull_request_id": pr_number},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {}


def deployed_ref(entry):
    deployment = entry.get("last_deployment")
    return deployment["git_ref"] if deployment else None


def app_name_in(payload):
    """Le nom d'app porté par une réponse Scalingo, dont la forme exacte n'est pas garantie."""
    return payload.get("app_name") if isinstance(payload, dict) else None


def ensure(client, bearer, parent_app, pr_number, sha):
    """Amène la review app de la PR à l'état voulu, quel que soit l'état constaté."""
    entry = find_review_app(client, bearer, parent_app, pr_number)
    if entry and deployed_ref(entry) == sha:
        return {"action": "noop", "app": entry["app_name"], "url": app_url(entry["app_name"])}
    created = deploy_review_app(client, bearer, parent_app, pr_number)
    name = app_name_in(entry) or app_name_in(created) or f"{parent_app}-pr{pr_number}"
    return {"action": "updated" if entry else "created", "app": name, "url": app_url(name)}


def destroy(client, bearer, parent_app, pr_number):
    """Supprime la review app de la PR. Une review app déjà absente vaut succès."""
    entry = find_review_app(client, bearer, parent_app, pr_number)
    if entry is None:
        return {"action": "absent", "app": None}
    name = entry["app_name"]
    response = client.request(
        "DELETE",
        f"{API_URL}/apps/{name}",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"current_name": name},
        timeout=TIMEOUT,
    )
    if response.status_code == 404:
        return {"action": "absent", "app": name}
    response.raise_for_status()
    return {"action": "destroyed", "app": name}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Réconcilie une review app Scalingo avec sa pull request.")
    parser.add_argument("command", choices=["ensure", "destroy"])
    parser.add_argument("--app", required=True, help="Application parente Scalingo")
    parser.add_argument("--pr", type=int, required=True, help="Numéro de la pull request")
    parser.add_argument("--sha", help="head.sha de la PR, requis pour ensure")
    args = parser.parse_args(argv)
    if args.command == "ensure" and not args.sha:
        parser.error("--sha est requis pour ensure")

    api_token = sys.stdin.read().strip()
    with httpx.Client() as client:
        bearer = exchange_token(client, api_token)
        if args.command == "ensure":
            result = ensure(client, bearer, args.app, args.pr, args.sha)
        else:
            result = destroy(client, bearer, args.app, args.pr)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
