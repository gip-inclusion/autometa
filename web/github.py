"""Minimal GitHub API client for PR creation."""

import logging

import httpx

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30,
        )

    def create_pr(self, title: str, branch: str, body: str = "", base: str = "main") -> str:
        """Create a pull request and return its URL."""
        resp = self._client.post(
            f"{GITHUB_API}/repos/{self.repo}/pulls",
            json={"title": title, "head": branch, "base": base, "body": body},
        )
        resp.raise_for_status()
        return resp.json()["html_url"]
