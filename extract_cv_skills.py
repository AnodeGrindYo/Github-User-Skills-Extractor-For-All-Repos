# Python 3.11+
# Entry compatible avec l'ancien script: `python extract_cv_skills.py`
from __future__ import annotations
import os, sys

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from cvskills_extractor.miner import PortfolioMiner
from cvskills_extractor.utils import compile_repo_patterns_from_env

def main():
    if load_dotenv is not None:
        load_dotenv()

    username = os.getenv("GITHUB_USERNAME","").strip()
    token = os.getenv("GITHUB_TOKEN","").strip()
    if not username or not token:
        print("Erreur: définir GITHUB_USERNAME et GITHUB_TOKEN (dans .env ou env).", file=sys.stderr)
        print("Exemple .env:\nGITHUB_USERNAME=TonPseudo\nGITHUB_TOKEN=ghp_xxx", file=sys.stderr)
        sys.exit(1)

    exclude_repo_patterns = compile_repo_patterns_from_env("EXCLUDE_REPOS")
    PortfolioMiner(username, token, exclude_repo_patterns).run()

if __name__ == "__main__":
    main()
