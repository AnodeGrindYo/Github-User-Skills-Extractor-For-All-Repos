from __future__ import annotations
import os, sys, argparse

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from .miner import PortfolioMiner
from .utils import compile_repo_patterns_from_env

def main(argv=None):
    if load_dotenv is not None:
        load_dotenv()

    parser = argparse.ArgumentParser(description="Infère les compétences à partir de vos repos GitHub (Markdown + JSON).")
    parser.add_argument("--username", default=os.getenv("GITHUB_USERNAME","").strip(), help="Nom d'utilisateur GitHub")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN","").strip(), help="Token GitHub (scope repo si besoin)")
    args = parser.parse_args(argv)

    if not args.username or not args.token:
        print("Erreur: définir GITHUB_USERNAME et GITHUB_TOKEN (ou passer --username/--token).", file=sys.stderr)
        print("Exemple .env:\nGITHUB_USERNAME=TonPseudo\nGITHUB_TOKEN=ghp_xxx", file=sys.stderr)
        sys.exit(1)

    exclude_repo_patterns = compile_repo_patterns_from_env("EXCLUDE_REPOS")
    PortfolioMiner(args.username, args.token, exclude_repo_patterns).run()

if __name__ == "__main__":
    main()
