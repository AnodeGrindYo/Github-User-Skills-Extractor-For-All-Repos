from __future__ import annotations
import os, sys, re, pathlib, datetime
from typing import List

from .config import EXCLUDE_DIRS, EXCLUDE_FILE_SUBSTR

def is_excluded(path: str) -> bool:
    p = pathlib.PurePosixPath(path)
    for part in p.parts:
        if part in ("", "/"):
            continue
        if part.lower() in EXCLUDE_DIRS:
            return True
    low = str(p.as_posix()).lower()
    return any(s in low for s in EXCLUDE_FILE_SUBSTR)

def compile_repo_patterns_from_env(env_var: str = "EXCLUDE_REPOS") -> List[re.Pattern]:
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

def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)
