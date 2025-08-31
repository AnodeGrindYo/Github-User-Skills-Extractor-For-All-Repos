from __future__ import annotations
import os, re, json, pathlib, datetime
from typing import Any, Dict, List, Optional, Tuple

from .github_http import GitHubHTTP
from .evidence import SkillIndex
from .rules import SkillRules
from .analyzer import RepoAnalyzer

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
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(doc)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
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
            if not placed:
                others.append((s, sc))

        def topn(lst, n=12):
            lst.sort(key=lambda x: -x[1]); return [name for name,_ in lst[:n]]

        lines = ["## Compétences démontrées par mes repositories"]
        for cat in SkillRules.CATEGORIES.keys():
            items = topn(by_cat[cat], n=12)
            if items:
                lines.append(f"**{cat}** : " + ", ".join(items))
        if others:
            items = topn(others, n=20)
            lines.append("**Autres** : " + ", ".join(items))

        # 2) PREUVES COMPLÈTES — toutes les lignes, sans troncage
        lines.append("\n<details open><summary><strong>Preuves complètes (toutes)</strong></summary>\n")
        for s, sc, r, whys in agg:
            lines.append(f"\n### {s}  \nScore total: {sc:.2f} • Repos distincts: {r}")
            lines.extend(whys)
        lines.append("\n</details>\n")
        return "\n".join(lines)
