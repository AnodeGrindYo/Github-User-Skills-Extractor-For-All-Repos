from __future__ import annotations
import json, base64, time, urllib.request, urllib.error, urllib.parse
from typing import Any, Dict, List, Optional

class GitHubHTTP:
    api = "https://api.github.com"

    def __init__(self, username: str, token: str):
        self.username = username
        self.token = token

    def _req(self, url: str) -> Any:
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if self.token:
            auth = f"{self.username}:{self.token}".encode()
            req.add_header("Authorization", "Basic " + base64.b64encode(auth).decode())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code} on {url} :: {body[:200]}")

    def list_repos(self, per_page=100, include_private=True) -> List[Dict[str, Any]]:
        repos, page = [], 1
        endpoint = (
            f"/user/repos?per_page={per_page}&page="
            if include_private
            else f"/users/{self.username}/repos?per_page={per_page}&page="
        )
        while True:
            url = self.api + endpoint + str(page)
            try:
                batch = self._req(url)
            except RuntimeError as e:
                if include_private and ("HTTP 401" in str(e) or "HTTP 403" in str(e)):
                    print("[!] Token insuffisant pour /user/repos — fallback public.")
                    include_private = False
                    endpoint = f"/users/{self.username}/repos?per_page={per_page}&page="
                    page, repos = 1, []
                    continue
                raise
            if not batch:
                break
            repos.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
            time.sleep(0.10)
        return repos

    def repo_tree(self, owner: str, repo: str, ref: str):
        url = f"{self.api}/repos/{owner}/{repo}/git/trees/{urllib.parse.quote(ref)}?recursive=1"
        return self._req(url)

    def get_file(self, owner: str, repo: str, path: str, ref: str) -> Optional[str]:
        url = f"{self.api}/repos/{owner}/{repo}/contents/{urllib.parse.quote(path)}?ref={urllib.parse.quote(ref)}"
        try:
            data = self._req(url)
        except RuntimeError:
            return None
        if isinstance(data, dict) and data.get("encoding") == "base64":
            try:
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            except Exception:
                return None
        if isinstance(data, dict) and isinstance(data.get("content"), str):
            return data["content"]
        return None
