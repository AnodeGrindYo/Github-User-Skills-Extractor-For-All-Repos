# extract_cv_skills.py
# Python 3.11+
# Explore GitHub repos, infer demonstrated skills, emit Markdown+JSON.
from __future__ import annotations
import os, sys, time, json, base64, math, re, pathlib, datetime
import urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree as ET
import tomllib
from typing import Dict, List, Any, Optional, Tuple, Set

# ---- .env ----------------------------------------------------------
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ---- Config pondération/langages -----------------------------------
# Baisser l'impact "Languages (GitHub)" et ignorer les tout-petits %
LANG_MIN_FRACTION = 0.08           # Ignore languages under 8% of bytes
LANG_BASE = 0.4                    # base weight for language signal
LANG_SLOPE = 1.0                   # slope × fraction

# ---- Exclusions répertoires & fichiers vendored --------------------
EXCLUDE_DIRS = {
    # classiques
    "node_modules","bower_components","vendor",".venv","venv","env",".env",".git",
    "__pycache__",".ipynb_checkpoints",".mypy_cache",".pytest_cache",
    "dist","build",".next","out","target",".terraform","coverage","site-packages",
    ".cache",".gradle",".idea",".vscode",
    # vendored/externes fréquents
    "lib","libs","third_party","third-party","external","externals","sdk","sdks",
    "samples","sample","examples","example","demos","demo",
}
# fichiers/segments typiques à ignorer (sous-modules ou libs packagées)
EXCLUDE_FILE_SUBSTR = {
    "mysql-connector", "bootstrap", "jquery", "three.min.js", "minified/", "min/",
}

def is_excluded(path: str) -> bool:
    p = pathlib.PurePosixPath(path)
    for part in p.parts:
        if part in ("", "/"): 
            continue
        if part.lower() in EXCLUDE_DIRS:
            return True
    low = str(p.as_posix()).lower()
    return any(s in low for s in EXCLUDE_FILE_SUBSTR)

# ---- GitHub HTTP ---------------------------------------------------
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
            try: body = e.read().decode("utf-8", errors="replace")
            except Exception: pass
            raise RuntimeError(f"HTTP {e.code} on {url} :: {body[:200]}")

    def list_repos(self, per_page=100, include_private=True) -> List[Dict[str, Any]]:
        repos, page = [], 1
        endpoint = f"/user/repos?per_page={per_page}&page=" if include_private else f"/users/{self.username}/repos?per_page={per_page}&page="
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
            if not batch: break
            repos.extend(batch)
            if len(batch) < per_page: break
            page += 1
            time.sleep(0.10)
        return repos

    def repo_tree(self, owner: str, repo: str, ref: str) -> Dict[str, Any]:
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

# ---- Evidence & Aggregation ---------------------------------------
class Evidence:
    def __init__(self, skill: str, repo: str, weight: float, why: str):
        self.skill, self.repo, self.weight, self.why = skill, repo, weight, why

class SkillIndex:
    def __init__(self):
        self.evidence: Dict[str, List[Evidence]] = {}
        self._caps: Dict[tuple, float] = {}   # (skill, repo) -> cumulated weight
        self._seen: Set[tuple] = set()        # (skill, repo, why) to dedup
        # cap spécifique Jupyter par repo
        self.per_skill_cap: Dict[str, float] = {"Jupyter": 2.0}

    def add(self, skill: str, repo: str, weight: float, why: str, cap: float = 5.0):
        key = (skill, repo, why)
        if key in self._seen:
            return
        self._seen.add(key)

        eff_cap = min(cap, self.per_skill_cap.get(skill, cap))
        cap_key = (skill, repo)
        current = self._caps.get(cap_key, 0.0)
        allowed = max(0.0, eff_cap - current)
        if allowed <= 0: return
        w = min(weight, allowed)
        if w <= 0: return

        self._caps[cap_key] = current + w
        self.evidence.setdefault(skill, []).append(Evidence(skill, repo, w, why))

    def aggregate(self) -> List[Tuple[str, float, int, List[str]]]:
        out: List[Tuple[str, float, int, List[str]]] = []
        for skill, evids in self.evidence.items():
            score = sum(e.weight for e in evids)
            repos = len(set(e.repo for e in evids))
            whys = [f"- {e.repo}: {e.why} (+{e.weight:.2f})" for e in evids]
            out.append((skill, score, repos, whys))
        out.sort(key=lambda x: (-x[1], -x[2], x[0].lower()))
        return out

# ---- Rules ---------------------------------------------------------
class SkillRules:
    CATEGORIES = {
        "Langages": {"Python","TypeScript","JavaScript","Go","Java","C++","Rust","SQL","Shell"},
        "Frameworks & Libs": {"Node.js","Express","NestJS","Angular","React","Next.js","Vue","FastAPI","Django","Flask","Pandas","NumPy","scikit-learn","PyTorch","TensorFlow"},
        "Data & MLOps": {"Jupyter","MLflow","Weights & Biases","Airflow","DVC","Great Expectations"},
        "DevOps & Cloud": {"Docker","Docker Compose","Kubernetes","Helm","Terraform","Ansible","Packer","GitHub Actions","GitLab CI","Jenkins","ArgoCD","Vault","Prometheus","Grafana","NGINX","AWS","GCP","Azure"},
        "Bases de données & MQ": {"PostgreSQL","MySQL","MongoDB","Redis","SQLite","Elasticsearch","RabbitMQ","Kafka"},
        "Qualité & Tests": {"PyTest","Jest","Vitest","Cypress","Playwright","Prettier","ESLint","Black","Ruff","Mypy"},
        "Build & Outillage": {"poetry","pip-tools","pipenv","Makefile","Vite","Webpack","Rollup","Gradle","Maven"},
        "Sécu & Observabilité": {"Snyk","Trivy","Bandit","Semgrep","OpenAPI","Sentry","OpenTelemetry"},
    }

    # Python-only
    PY_DEP_TO_SKILL = {
        "pandas":"Pandas","numpy":"NumPy","scikit-learn":"scikit-learn",
        "torch":"PyTorch","tensorflow":"TensorFlow","mlflow":"MLflow",
        "dvc":"DVC","great-expectations":"Great Expectations","jupyter":"Jupyter",
        "fastapi":"FastAPI","django":"Django","flask":"Flask",
        "pytest":"PyTest","black":"Black","ruff":"Ruff","mypy":"Mypy",
        "sentry-sdk":"Sentry",
    }
    # JS-only
    JS_DEP_TO_SKILL = {
        "react":"React","next":"Next.js","vue":"Vue","express":"Express","nestjs":"NestJS","@nestjs/core":"NestJS",
        "@angular/core":"Angular",
        "vite":"Vite","webpack":"Webpack","rollup":"Rollup",
        "jest":"Jest","vitest":"Vitest","cypress":"Cypress","playwright":"Playwright",
        "prettier":"Prettier","eslint":"ESLint",
        "opentelemetry-api":"OpenTelemetry","@sentry/browser":"Sentry","@sentry/node":"Sentry"
    }

    FILE_HINTS: List[Tuple[str,str,float]] = [
        (r"^Dockerfile$", "Docker", 2.0),
        (r"^docker-compose\.ya?ml$", "Docker Compose", 2.0),
        (r"(^|/)\.github/workflows/.*\.ya?ml$", "GitHub Actions", 2.2),
        (r"(^|/)Jenkinsfile$", "Jenkins", 2.1),
        (r"(^|/)\.gitlab-ci\.ya?ml$", "GitLab CI", 2.1),
        (r"\.tf$", "Terraform", 2.0),
        (r"(^|/)charts/.*/Chart\.ya?ml$", "Helm", 2.0),
        (r"(^|/)k8s/.+\.ya?ml$", "Kubernetes", 2.0),
        (r"(^|/)manifests?/.+\.ya?ml$", "Kubernetes", 1.6),
        (r"^Makefile$", "Makefile", 1.0),
        (r"\.ipynb$", "Jupyter", 1.0),
        (r"(^|/)(docker|compose)\.ya?ml$", "Docker Compose", 1.6),
        (r"(^|/)openapi\.ya?ml$", "OpenAPI", 1.2),
        (r"(^|/)poetry\.lock$", "poetry", 1.0),
        (r"(^|/)requirements\.txt$", "Python", 0.0),
        (r"(^|/)pyproject\.toml$", "Python", 0.4),
        (r"(^|/)Pipfile(\.lock)?$", "Python", 0.2),
        (r"^package\.json$", "Node.js", 0.3),
        (r"(^|/)go\.mod$", "Go", 1.5),
        (r"(^|/)Cargo\.toml$", "Rust", 1.5),
        (r"(^|/)pom\.xml$", "Java", 1.5),
        (r"(^|/)build\.gradle(\.kts)?$", "Java", 1.2),
        (r"\.(sql|db|sqlite)$", "SQL", 0.6),
        (r"\.(sh|bash)$", "Shell", 0.6),
    ]

    @staticmethod
    def map_language(name: str) -> Optional[str]:
        mapping = {
            "Python":"Python","JavaScript":"JavaScript","TypeScript":"TypeScript","Go":"Go",
            "Rust":"Rust","C++":"C++","C":"C++","Java":"Java","Shell":"Shell",
            "Jupyter Notebook":"Jupyter","HTML":None,"CSS":None,"SCSS":None
        }
        return mapping.get(name, None)

# ---- Repo Analyzer -------------------------------------------------
class RepoAnalyzer:
    def __init__(self, gh: GitHubHTTP, owner: str, repo_meta: Dict[str, Any]):
        self.gh = gh
        self.owner = owner
        self.repo = repo_meta["name"]
        self.meta = repo_meta
        self.default_branch = repo_meta.get("default_branch","main")

    def recency_factor(self) -> float:
        pushed = self.meta.get("pushed_at")
        if not pushed: return 1.0
        dt = datetime.datetime.fromisoformat(pushed.replace("Z","+00:00"))
        days = (datetime.datetime.now(datetime.timezone.utc) - dt).days
        if days <= 30: return 1.5
        if days <= 180: return 1.3
        if days <= 365: return 1.1
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
        if tree is None: raise last_err

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
                        if isinstance(d, dict): deps.update(d)
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
                        for part in sec.split("."): d = d.get(part, {})
                        val = d.get("dependencies")
                        if isinstance(val, dict):
                            deps += list(val.keys())
                        elif isinstance(val, list):
                            deps += val
                        grp = d.get("group", {})
                        if isinstance(grp, dict):
                            for g in grp.values():
                                gd = g.get("dependencies", {})
                                if isinstance(gd, dict): deps += list(gd.keys())
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
                    if not pkg or pkg.startswith("#"): continue
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

# ---- Portfolio Miner ----------------------------------------------
class PortfolioMiner:
    def __init__(self, username: str, token: str, exclude_repo_patterns: Optional[List[re.Pattern]] = None):
        self.gh = GitHubHTTP(username, token)
        self.username = username
        self.exclude_repo_patterns = exclude_repo_patterns or []

    def _is_repo_excluded(self, name: str) -> bool:
        return any(p.search(name) for p in self.exclude_repo_patterns)

    def run(self) -> Dict[str, Any]:
        print(f"[*] Utilisateur GitHub: {self.username}")
        print("[*] Listing repositories…")
        repos = self.gh.list_repos(include_private=True)
        repos = [r for r in repos if not r.get("fork") and not r.get("archived")]
        if self.exclude_repo_patterns:
            before = len(repos)
            repos = [r for r in repos if not self._is_repo_excluded(r.get("name",""))]
            print(f"    Filtre EXCLUDE_REPOS: {before - len(repos)} repo(s) exclus")
        print(f"    {len(repos)} repos à analyser")
        if not repos:
            print("[!] Aucun repo accessible après filtrage.")
            return {"markdown": None, "json": None}

        global_idx = SkillIndex()
        for r in repos:
            name, owner = r["name"], r["owner"]["login"]
            try:
                print(f"[+] {owner}/{name}")
                idx = RepoAnalyzer(self.gh, owner, r).analyze()
                for skill, evids in idx.evidence.items():
                    for e in evids:
                        global_idx.add(e.skill, e.repo, e.weight, e.why)
            except Exception as ex:
                print(f"    ! Erreur sur {owner}/{name}: {ex}")

        aggregated = global_idx.aggregate()
        if not aggregated:
            print("[!] Aucune compétence n'a pu être inférée.")
        doc = self._to_cv_markdown(aggregated)
        json_data = self._to_json(aggregated)

        out_md, out_json = "cv_skills.md", "skills.json"
        with open(out_md, "w", encoding="utf-8") as f: f.write(doc)
        with open(out_json, "w", encoding="utf-8") as f: json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"[*] Généré: {out_md} & {out_json}")
        return {"markdown": out_md, "json": out_json}

    def _to_json(self, agg: List[Tuple[str, float, int, List[str]]]) -> Dict[str, Any]:
        return {
            "generated_at": datetime.datetime.now().isoformat(),
            "skills": [
                {"skill": s, "score": round(sc,2), "repos": r, "evidence": whys}
                for (s, sc, r, whys) in agg
            ],
        }

    def _to_cv_markdown(self, agg: List[Tuple[str, float, int, List[str]]]) -> str:
        # 1) résumé par catégories
        by_cat: Dict[str, List[Tuple[str,float]]] = {c:[] for c in SkillRules.CATEGORIES.keys()}
        others: List[Tuple[str,float]] = []
        for s, sc, r, _ in agg:
            placed = False
            for cat, items in SkillRules.CATEGORIES.items():
                if s in items:
                    by_cat[cat].append((s, sc)); placed = True; break
            if not placed: others.append((s, sc))

        def topn(lst, n=12):
            lst.sort(key=lambda x: -x[1]); return [name for name,_ in lst[:n]]

        lines = ["## Compétences démontrées par mes repositories"]
        for cat in SkillRules.CATEGORIES.keys():
            items = topn(by_cat[cat], n=12)
            if items: lines.append(f"**{cat}** : " + ", ".join(items))
        if others:
            items = topn(others, n=20)
            lines.append("**Autres** : " + ", ".join(items))

        # 2) PREUVES COMPLÈTES — toutes les lignes, sans troncage
        lines.append("\n<details open><summary><strong>Preuves complètes (toutes)</strong></summary>\n")
        for s, sc, r, whys in agg:
            lines.append(f"\n### {s}  \nScore total: {sc:.2f} • Repos distincts: {r}")
            # aucune limitation: on imprime toutes les whys
            lines.extend(whys)
        lines.append("\n</details>\n")
        return "\n".join(lines)

# ---- Entry ---------------------------------------------------------
def _compile_repo_patterns_from_env(env_var: str = "EXCLUDE_REPOS") -> List[re.Pattern]:
    raw = os.getenv(env_var, "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    compiled: List[re.Pattern] = []
    for p in parts:
        try:
            compiled.append(re.compile(p, flags=re.IGNORECASE))
        except re.error as e:
            print(f"[!] Regex invalide dans {env_var}: {p} ({e}) — ignoré.", file=sys.stderr)
    return compiled

def main():
    if load_dotenv is not None:
        load_dotenv()

    username = os.getenv("GITHUB_USERNAME","").strip()
    token = os.getenv("GITHUB_TOKEN","").strip()
    if not username or not token:
        print("Erreur: définir GITHUB_USERNAME et GITHUB_TOKEN (dans .env ou env).", file=sys.stderr)
        print("Exemple .env:\nGITHUB_USERNAME=TonPseudo\nGITHUB_TOKEN=ghp_xxx", file=sys.stderr)
        sys.exit(1)

    exclude_repo_patterns = _compile_repo_patterns_from_env("EXCLUDE_REPOS")
    PortfolioMiner(username, token, exclude_repo_patterns).run()

if __name__ == "__main__":
    main()
