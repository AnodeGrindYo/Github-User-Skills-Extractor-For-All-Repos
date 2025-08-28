# 📊 GitHub Portfolio Skill Extractor

Ce projet est un **outil Python** qui parcourt automatiquement vos repositories GitHub (publics et privés, si votre token le permet), analyse leur contenu et en déduit les **compétences techniques démontrées**.  

Il génère deux fichiers de sortie :  
- `cv_skills.md` → résumé lisible en Markdown (avec toutes les preuves)  
- `skills.json` → export structuré et exploitable par d’autres outils  

---

## 🚀 Fonctionnement

### 1. Collecte des repositories
L’outil se connecte à l’API GitHub via votre **token personnel**.  
- Il liste vos repositories (hors forks et archives).  
- Il peut exclure certains dépôts (ex. démos, cours, exercices) via des regex définies dans `.env`.

### 2. Analyse de chaque repository
Pour chaque repo, plusieurs signaux sont utilisés :  

- **Langages déclarés** par GitHub (`/languages`)  
  - Pondérés faiblement, ignorés si < 8 % du code  
- **Présence de fichiers clés**  
  - `Dockerfile`, `.github/workflows/*`, `pyproject.toml`, `package.json`, `pom.xml`, etc.  
  - Déduisent des compétences spécifiques (Docker, GitHub Actions, Python, Node.js, etc.)  
- **Dépendances déclarées**  
  - Python : `requirements.txt`, `pyproject.toml` (Poetry, PEP 621)  
  - JS/TS : `package.json`  
  - Java : `pom.xml`, `build.gradle`  
- **Manifests Kubernetes / Helm**  
- **Recency & Popularity**  
  - Score ajusté selon la **fraîcheur des commits** et la **popularité** (stars, forks)  

### 3. Pondération & preuves
Chaque détection est stockée comme une **preuve** :  
- `skill` (compétence identifiée)  
- `repo` (projet dans lequel elle est trouvée)  
- `weight` (poids/scoring)  
- `why` (raison précise : fichier, dépendance, etc.)  

Des plafonds évitent qu’un seul repo “gonfle artificiellement” un skill (ex. Jupyter est limité à 2.0 points max par repo).

---

## ⚙️ Installation

1. **Cloner le repo**
```bash
git clone https://github.com/ton-compte/auto_github_repo_extract.git
cd auto_github_repo_extract
```

2. **Créer un environnement virtuel**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows PowerShell
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d’environnement**
Créer un fichier `.env` :
```ini
GITHUB_USERNAME=TonPseudo
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxx
# Optionnel : exclure des repos par regex
EXCLUDE_REPOS=^angular_,phonecat,(-|_)exercices?
```

5. **Exécuter le script**
```bash
python extract_cv_skills.py
```

---

## 📂 Fichiers générés

### 1. `cv_skills.md`
Fichier lisible en Markdown, adapté à une intégration dans un CV ou portfolio.

Structure :  
```markdown
## Compétences démontrées par mes repositories
**Langages** : Python, JavaScript, TypeScript
**Frameworks & Libs** : React, Django, FastAPI
**DevOps & Cloud** : Docker, Kubernetes, GitHub Actions

<details open><summary><strong>Preuves complètes (toutes)</strong></summary>

### Python  
Score total: 12.4 • Repos distincts: 6
- Projet1: File hint: pyproject.toml (+0.40)
- Projet2: requirements: pandas (+1.60)
- Projet3: pyproject dep: scikit-learn (+1.80)

### Docker  
Score total: 6.2 • Repos distincts: 3
- ProjetA: File hint: Dockerfile (+2.00)
- ProjetB: File hint: docker-compose.yml (+2.00)

...
</details>
```

👉 Chaque compétence inclut :  
- **Score total** : somme des poids attribués  
- **Repos distincts** : nombre de projets où la compétence est démontrée  
- **Preuves détaillées** : fichiers/dépendances qui justifient la détection  

---

### 2. `skills.json`
Export structuré pour exploitation automatique (dashboards, scripts…).

Exemple :  
```json
{
  "generated_at": "2025-08-28T12:34:56",
  "skills": [
    {
      "skill": "Python",
      "score": 12.4,
      "repos": 6,
      "evidence": [
        "- Projet1: File hint: pyproject.toml (+0.40)",
        "- Projet2: requirements: pandas (+1.60)",
        "- Projet3: pyproject dep: scikit-learn (+1.80)"
      ]
    },
    {
      "skill": "Docker",
      "score": 6.2,
      "repos": 3,
      "evidence": [
        "- ProjetA: File hint: Dockerfile (+2.00)",
        "- ProjetB: File hint: docker-compose.yml (+2.00)"
      ]
    }
  ]
}
```

Champs :  
- `skill` : nom de la compétence  
- `score` : score pondéré total  
- `repos` : nombre de dépôts distincts  
- `evidence` : liste exhaustive des preuves collectées  

---

## 🔧 Personnalisation

- **Exclure des repos** : via regex dans `.env` (`EXCLUDE_REPOS`)  
- **Ajuster les poids** : modifier les constantes dans le code (`FILE_HINTS`, `LANG_MIN_FRACTION`, etc.)  
- **Ajouter de nouvelles règles** : enrichir `SkillRules` (nouveaux frameworks, libs, patterns de fichiers…)  

---

## 📜 Licence

Projet open-source — libre à toi de le modifier pour ton usage personnel ou pro.
