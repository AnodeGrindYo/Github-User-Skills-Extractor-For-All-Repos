# cvskills_extractor

Exploration de repositories GitHub pour inférer des **compétences démontrées** à partir de :
- Langages détectés par l'API GitHub
- Fichiers indicateurs (Dockerfile, Jenkinsfile, manifests K8s, etc.)
- Dépendances (Python via `pyproject.toml`/`requirements*.txt`, JavaScript via `package.json`)
- Heuristiques (recence, popularité)

Sorties :
- `cv_skills.md` : aperçu Markdown synthétique + **toutes les preuves détaillées**
- `skills.json` : données structurées (score, nb de repos, explications)

## Installation

```bash
python -m venv .venv
# Windows:   .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Créez un fichier `.env` à la racine (ou exportez des variables d'environnement) :
```ini
GITHUB_USERNAME=TonPseudo
GITHUB_TOKEN=ghp_xxx
# Optionnel: patterns regex séparés par des virgules pour exclure certains repos
EXCLUDE_REPOS=^fork-.*, (demo|playground)$
```

## Utilisation

```bash
# Depuis la racine du repo
python -m cvskills_extractor.cli
# OU
python -m cvskills_extractor.cli --username TonPseudo --token ghp_xxx
```

Les fichiers `cv_skills.md` et `skills.json` seront générés dans le répertoire courant.

## Architecture

- `config.py` : constantes & paramètres
- `utils.py` : utilitaires (exclusions, regex, temps)
- `github_http.py` : client GitHub minimal
- `evidence.py` : modèles de données & agrégation
- `rules.py` : correspondances fichiers/dépendances → compétences
- `analyzer.py` : analyse d'un repository
- `miner.py` : orchestration multi‑repos + rendu (Markdown/JSON)
- `cli.py` : point d'entrée (env `.env`, arguments, erreurs claires)

## Licence

MIT
