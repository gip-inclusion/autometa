"""Réconcilie les review apps Scalingo avec le cycle de vie des pull requests GitHub."""

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
        if entry["pull_request"]["number"] == pr_number:
            return entry
    return None


def app_url(app_name):
    return f"https://{app_name}.osc-fr1.scalingo.io"
