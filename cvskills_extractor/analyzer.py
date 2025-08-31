from __future__ import annotations
import re, math, json, pathlib, datetime, xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

import tomllib

from .github_http import GitHubHTTP
from .evidence import SkillIndex
from .rules import SkillRules
from .config import LANG_MIN_FRACTION, LANG_BASE, LANG_SLOPE
from .utils import is_excluded, utcnow

class RepoAnalyzer:
    def __init__(self, gh: GitHubHTTP, owner: str, repo_meta: Dict[str, Any]):
        self.gh = gh
        self.owner = owner
        self.repo = repo_meta["name"]
        self.meta = repo_meta
        self.default_branch = repo_meta.get("default_branch","main")

    def recency_factor(self) -> float:
        pushed = self.meta.get("pushed_at")
        if not pushed:
            return 1.0
        dt = datetime.datetime.fromisoformat(pushed.replace("Z","+00:00"))
        days = (utcnow() - dt).days
        if days <= 30:
            return 1.5
        if days <= 180:
            return 1.3
        if days <= 365:
            return 1.1
        return 1.0

    def popularity_factor(self) -> float:
        stars = self.meta.get("stargazers_count", 0)
        forks = self.meta.get("forks_count", 0)
        return 1.0 + min(0.5, math.log10(1+stars+0.5*forks)/4)

    def analyze(self) -> SkillIndex:
        idx = SkillIndex()

        # 1) Languages (min fraction & lighter slope)
        for lang, basew in self._languages_hint():
            idx.add(lang, self.repo, basew*self.recency_factor()*self.popularity_factor(), "Languages (GitHub)")

        # 2) Tree (fallback refs)
        refs_to_try = [self.default_branch, "main", "master", "HEAD"]
        tree, last_err = None, None
        for ref in refs_to_try:
            try:
                tree = self.gh.repo_tree(self.owner, self.repo, ref)
                self.default_branch = ref
                break
            except Exception as e:
                last_err = e
        if tree is None:
            raise last_err

        paths = [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob"]
        paths = [p for p in paths if not is_excluded(p)]

        # 2a) File hints
        rfpf = self.recency_factor()*self.popularity_factor()
        for p in paths:
            for pat, skill, w in SkillRules.FILE_HINTS:
                if w <= 0:
                    continue
                if re.search(pat, p, flags=re.IGNORECASE):
                    idx.add(skill, self.repo, w*rfpf, f"File hint: {p}")

        # 2b) Dependencies
        # package.json (root only, JS map only)
        if "package.json" in {pathlib.PurePosixPath(p).name for p in paths}:
            content = self.gh.get_file(self.owner, self.repo, "package.json", self.default_branch)
            if content:
                try:
                    pkg = json.loads(content)
                    deps = {}
                    for k in ("dependencies","devDependencies","peerDependencies"):
                        d = pkg.get(k, {})
                        if isinstance(d, dict):
                            deps.update(d)
                    dep_keys = {str(k).lower() for k in deps.keys()}
                    for dep in dep_keys:
                        skill = SkillRules.JS_DEP_TO_SKILL.get(dep)
                        if skill:
                            idx.add(skill, self.repo, 1.8*rfpf, f"package.json dep: {dep}")
                    if "typescript" in dep_keys or ("tsconfig.json" in {pathlib.PurePosixPath(p).name for p in paths}):
                        idx.add("TypeScript", self.repo, 0.9*rfpf, "TypeScript config/deps")
                    if "@angular/core" in dep_keys:
                        idx.add("Angular", self.repo, 1.3*rfpf, "Angular deps")
                except Exception:
                    pass

        # pyproject.toml (Python map only)
        if any(pathlib.PurePosixPath(p).name == "pyproject.toml" for p in paths):
            content = self.gh.get_file(self.owner, self.repo, "pyproject.toml", self.default_branch)
            if content:
                try:
                    data = tomllib.loads(content)
                    deps: List[str] = []
                    for sec in ("project","tool.poetry"):
                        d = data
                        for part in sec.split("."):
                            d = d.get(part, {})
                        val = d.get("dependencies")
                        if isinstance(val, dict):
                            deps += list(val.keys())
                        elif isinstance(val, list):
                            deps += val
                        grp = d.get("group", {})
                        if isinstance(grp, dict):
                            for g in grp.values():
                                gd = g.get("dependencies", {})
                                if isinstance(gd, dict):
                                    deps += list(gd.keys())
                    deps_lower = [re.split(r"[<>=\[\](),]| ", str(x))[0].lower() for x in deps]
                    for dep in deps_lower:
                        skill = SkillRules.PY_DEP_TO_SKILL.get(dep)
                        if skill:
                            idx.add(skill, self.repo, 1.8*rfpf, f"pyproject dep: {dep}")
                except Exception:
                    pass

        # requirements*.txt (Python map only)
        req_paths = [p for p in paths if pathlib.PurePosixPath(p).name.lower().startswith("requirements") and p.lower().endswith(".txt")]
        for rp in req_paths:
            content = self.gh.get_file(self.owner, self.repo, rp, self.default_branch)
            if content:
                for line in content.splitlines():
                    pkg = re.split(r"[<>=\[\](),]| ", line.strip())[0].lower()
                    if not pkg or pkg.startswith("#"):
                        continue
                    skill = SkillRules.PY_DEP_TO_SKILL.get(pkg)
                    if skill:
                        idx.add(skill, self.repo, 1.6*rfpf, f"requirements: {pkg}")

        # Go / Rust / Java hints
        if any(pathlib.PurePosixPath(p).name=="go.mod" for p in paths):
            idx.add("Go", self.repo, 1.0*rfpf, "go.mod present")
        if any(pathlib.PurePosixPath(p).name=="Cargo.toml" for p in paths):
            idx.add("Rust", self.repo, 1.0*rfpf, "Cargo.toml present")
        if any(pathlib.PurePosixPath(p).name=="pom.xml" for p in paths):
            idx.add("Java", self.repo, 1.0*rfpf, "pom.xml present")
            content = self.gh.get_file(self.owner, self.repo, "pom.xml", self.default_branch)
            if content:
                try:
                    root = ET.fromstring(content)
                    for dep in root.findall(".//{*}dependency/{*}artifactId"):
                        name = (dep.text or "").lower()
                        if "spring-boot" in name:
                            idx.add("Spring Boot", self.repo, 1.2*rfpf, "pom.xml dep spring-boot")
                except Exception:
                    pass
        if any(pathlib.PurePosixPath(p).name in ("build.gradle","build.gradle.kts") for p in paths):
            idx.add("Java", self.repo, 0.8*rfpf, "Gradle present")

        # K8s heuristique
        for p in paths:
            if p.lower().endswith((".yaml",".yml")) and any(seg in p.lower() for seg in ("k8s/","manifests/","deploy","charts/","helm/")):
                content = self.gh.get_file(self.owner, self.repo, p, self.default_branch)
                if content and re.search(r"\bapiVersion:\s", content) and re.search(r"\bkind:\s", content):
                    idx.add("Kubernetes", self.repo, 0.8*rfpf, f"K8s manifest: {p}")

        return idx

    def _languages_hint(self) -> List[Tuple[str,float]]:
        url = f"{GitHubHTTP.api}/repos/{self.owner}/{self.repo}/languages"
        try:
            data = self.gh._req(url)
        except RuntimeError:
            return []
        total = sum(data.values()) or 1
        langs: List[Tuple[str,float]] = []
        for k,v in data.items():
            mapped = SkillRules.map_language(k)
            if not mapped:
                continue
            frac = v/total
            if frac < LANG_MIN_FRACTION:
                continue
            basew = LANG_BASE + LANG_SLOPE*frac
            langs.append((mapped, basew))
        return langs
