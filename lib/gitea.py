"""Gitea API client for self-hosted Gitea."""

import logging
from typing import Optional

import requests

from web import config

logger = logging.getLogger(__name__)


class GiteaClient:
    """Client for self-hosted Gitea API."""

    def __init__(self):
        self.base_url = config.GITEA_URL.rstrip("/")
        self.token = config.GITEA_API_TOKEN
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"token {self.token}"
        self._session.headers["Accept"] = "application/json"
        self._session.headers["Content-Type"] = "application/json"

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def create_repo(
        self,
        name: str,
        description: str = "",
        org: Optional[str] = None,
    ) -> dict:
        """Create a new repository, optionally under an organization."""
        payload = {
            "name": name,
            "description": description,
            "private": True,
            "auto_init": True,
            "default_branch": "main",
        }
        if org:
            url = self._url(f"/orgs/{org}/repos")
        elif config.GITEA_ORG:
            url = self._url(f"/orgs/{config.GITEA_ORG}/repos")
        else:
            url = self._url("/user/repos")

        resp = self._session.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_repo(self, owner: str, name: str) -> dict:
        """Get an existing repository by owner/name."""
        resp = self._session.get(self._url(f"/repos/{owner}/{name}"))
        resp.raise_for_status()
        return resp.json()

    def push_files(
        self,
        owner: str,
        repo: str,
        branch: str,
        files: dict[str, str],
        message: str,
    ) -> dict:
        """Push multiple files in a single commit via the contents API."""
        # Gitea's contents API is per-file, so we use the raw git API
        # via POST /repos/{owner}/{repo}/contents/{filepath}
        # For multi-file commits, we create files one by one.
        # A better approach for many files is git push, but for
        # small commits (spec, boilerplate) this works fine.
        results = []
        for path, content in files.items():
            import base64
            payload = {
                "message": message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch,
            }
            resp = self._session.post(
                self._url(f"/repos/{owner}/{repo}/contents/{path}"),
                json=payload,
            )
            resp.raise_for_status()
            results.append(resp.json())
        return results[-1] if results else {}

    def create_branch(self, owner: str, repo: str, branch: str, ref: str = "main") -> dict:
        """Create a new branch."""
        payload = {
            "new_branch_name": branch,
            "old_branch_name": ref,
        }
        resp = self._session.post(
            self._url(f"/repos/{owner}/{repo}/branches"),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        source: str,
        target: str,
        title: str,
    ) -> dict:
        """Create a pull request."""
        payload = {
            "head": source,
            "base": target,
            "title": title,
        }
        resp = self._session.post(
            self._url(f"/repos/{owner}/{repo}/pulls"),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def get_repo(self, owner: str, repo: str) -> dict:
        """Get repository details."""
        resp = self._session.get(self._url(f"/repos/{owner}/{repo}"))
        resp.raise_for_status()
        return resp.json()

    def delete_repo(self, owner: str, repo: str) -> None:
        """Delete a repository."""
        resp = self._session.delete(self._url(f"/repos/{owner}/{repo}"))
        resp.raise_for_status()

    def create_webhook(
        self,
        owner: str,
        repo: str,
        url: str,
        secret: str,
        events: list[str] | None = None,
        branch_filter: str | None = None,
    ) -> dict:
        """Create a webhook on a repository."""
        payload = {
            "type": "gitea",
            "active": True,
            "config": {
                "url": url,
                "content_type": "json",
                "secret": secret,
            },
            "events": events or ["push"],
        }
        if branch_filter:
            payload["branch_filter"] = branch_filter
        resp = self._session.post(
            self._url(f"/repos/{owner}/{repo}/hooks"),
            json=payload,
        )
        if resp.status_code in (409, 422):
            # Hook may already exist; return a matching hook when possible.
            for hook in self.list_webhooks(owner, repo):
                hook_url = ((hook.get("config") or {}).get("url") or "").strip()
                hook_filter = (hook.get("branch_filter") or "").strip()
                if hook_url == url and (not branch_filter or hook_filter == branch_filter):
                    return hook
        resp.raise_for_status()
        return resp.json()

    def list_webhooks(self, owner: str, repo: str) -> list[dict]:
        """List repository webhooks."""
        resp = self._session.get(self._url(f"/repos/{owner}/{repo}/hooks"))
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    def version(self) -> str:
        """Get Gitea server version."""
        resp = self._session.get(self._url("/version"))
        resp.raise_for_status()
        return resp.json().get("version", "unknown")
