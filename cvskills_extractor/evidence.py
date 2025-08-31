from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

@dataclass
class Evidence:
    skill: str
    repo: str
    weight: float
    why: str

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
        if allowed <= 0:
            return
        w = min(weight, allowed)
        if w <= 0:
            return

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
