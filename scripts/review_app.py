"""Réconcilie les review apps Scalingo avec le cycle de vie des pull requests GitHub."""

import argparse
import json
import sys
import time

import httpx

AUTH_URL = "https://auth.scalingo.com/v1/tokens/exchange"
API_URL = "https://api.osc-fr1.scalingo.com/v1"
TIMEOUT = 30.0
# Why: la création provisionne les addons avant de répondre — mesurée à 17 s, elle déborde TIMEOUT
CREATE_TIMEOUT = 300.0
# Why: l'addon PostgreSQL met une soixantaine de secondes à passer "running"
ADDONS_TIMEOUT = 300.0
ADDONS_POLL_SECONDS = 10.0
# Why: build mesuré à ~2 min, plus la marge d'une file d'attente Scalingo
DEPLOYMENT_TIMEOUT = 900.0
DEPLOYMENT_POLL_SECONDS = 15.0
PENDING_STATUSES = frozenset({"queued", "building", "pushing", "starting"})


def headers(bearer):
    return {"Authorization": f"Bearer {bearer}"}


def exchange_token(client, api_token):
    """Échange un token API Scalingo contre un bearer JWT de courte durée."""
    response = client.post(AUTH_URL, auth=("", api_token), timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["token"]


def scm_repo_link(client, bearer, parent_app):
    """La configuration du lien SCM de l'app parente."""
    response = client.get(f"{API_URL}/apps/{parent_app}/scm_repo_link", headers=headers(bearer), timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["scm_repo_link"]


def find_review_app(client, bearer, parent_app, pr_number):
    """La review app rattachée à cette PR, ou None."""
    response = client.get(
        f"{API_URL}/apps/{parent_app}/scm_repo_link/review_apps",
        headers=headers(bearer),
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


def create_review_app(client, bearer, parent_app, pr_number):
    """Crée la review app et provisionne ses addons. Ne la déploie pas."""
    response = client.post(
        f"{API_URL}/apps/{parent_app}/scm_repo_link/manual_review_app",
        headers=headers(bearer),
        json={"pull_request_id": pr_number},
        timeout=CREATE_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["review_app"]


def wait_for_addons(client, bearer, app_name, timeout=ADDONS_TIMEOUT):
    """Attend que les addons soient provisionnés : DATABASE_URL n'existe qu'à ce moment-là."""
    deadline = time.monotonic() + timeout
    while True:
        response = client.get(f"{API_URL}/apps/{app_name}/addons", headers=headers(bearer), timeout=TIMEOUT)
        response.raise_for_status()
        addons = response.json()["addons"]
        if addons and all(addon["status"] == "running" for addon in addons):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f"addons de {app_name} toujours pas prêts après {timeout} s")
        time.sleep(ADDONS_POLL_SECONDS)


def deploy(client, bearer, app_name, branch):
    """Lance le déploiement d'une branche sur une review app existante."""
    response = client.post(
        f"{API_URL}/apps/{app_name}/scm_repo_link/manual_deploy",
        headers=headers(bearer),
        json={"branch": branch},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["deployment"]["id"]


def wait_for_deployment(client, bearer, app_name, deployment_id, timeout=DEPLOYMENT_TIMEOUT):
    """Attend la fin du build : sans ça, un hook-error passerait pour un déploiement réussi."""
    deadline = time.monotonic() + timeout
    while True:
        response = client.get(
            f"{API_URL}/apps/{app_name}/deployments/{deployment_id}",
            headers=headers(bearer),
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        status = response.json()["deployment"]["status"]
        if status not in PENDING_STATUSES:
            if status != "success":
                raise RuntimeError(f"déploiement de {app_name} terminé en {status}")
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f"déploiement de {app_name} toujours en {status} après {timeout} s")
        time.sleep(DEPLOYMENT_POLL_SECONDS)


def deployed_ref(entry):
    """Le SHA effectivement en ligne : un déploiement échoué ne compte pas comme déployé."""
    deployment = entry.get("last_deployment")
    if not deployment or deployment.get("status") != "success":
        return None
    return deployment["git_ref"]


def ensure(client, bearer, parent_app, pr_number, sha):
    """Amène la review app de la PR à l'état voulu, quel que soit l'état constaté."""
    if not scm_repo_link(client, bearer, parent_app)["delete_on_close_enabled"]:
        raise RuntimeError("delete_on_close_enabled est désactivé : rien ne détruirait plus les review apps")

    entry = find_review_app(client, bearer, parent_app, pr_number)
    if entry and deployed_ref(entry) == sha:
        return {"action": "noop", "app": entry["app_name"], "url": app_url(entry["app_name"])}

    action = "updated"
    if entry is None:
        entry = create_review_app(client, bearer, parent_app, pr_number)
        wait_for_addons(client, bearer, entry["app_name"])
        action = "created"

    name = entry["app_name"]
    deployment_id = deploy(client, bearer, name, entry["pull_request"]["branch_name"])
    wait_for_deployment(client, bearer, name, deployment_id)
    return {"action": action, "app": name, "url": app_url(name)}


def stop(client, bearer, parent_app, pr_number):
    """Éteint la review app de la PR : un collaborateur peut scaler à zéro, pas supprimer."""
    entry = find_review_app(client, bearer, parent_app, pr_number)
    if entry is None:
        return {"action": "absent", "app": None}
    name = entry["app_name"]
    response = client.post(
        f"{API_URL}/apps/{name}/scale",
        headers=headers(bearer),
        json={"containers": [{"name": "web", "amount": 0}]},
        timeout=TIMEOUT,
    )
    if response.status_code == 404:
        return {"action": "absent", "app": name}
    response.raise_for_status()
    return {"action": "stopped", "app": name}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Réconcilie une review app Scalingo avec sa pull request.")
    parser.add_argument("command", choices=["ensure", "stop"])
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
            result = stop(client, bearer, args.app, args.pr)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
