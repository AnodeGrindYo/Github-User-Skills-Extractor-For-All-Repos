from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple

"""
SkillRules
----------
Un référentiel enrichi de catégories RH + mappages de dépendances & d'indices de fichiers
→ compétences détectables dans les repositories.

Objectifs RH :
- Couvrir un spectre large (backend, frontend, data, MLOps, cloud, SRE, sécurité, mobile, BI).
- Multiplier les heuristiques faibles mais nombreuses pour réduire les faux négatifs.
- Standardiser les libellés de compétences (ex.: "Node.js", "React", "AWS", "Terraform").
- Rester purement déclaratif ici : aucune logique d'analyse (tenue par analyzer.py).
"""

class SkillRules:
    # -----------------------------
    # Catégories (affichage CV)
    # -----------------------------
    CATEGORIES: Dict[str, set] = {
        # Langages & paradigmes
        "Langages": {
            "Python","TypeScript","JavaScript","Go","Java","C","C++","C#","Rust","Scala","Kotlin","PHP","Ruby","R",
            "SQL","NoSQL","Shell","Bash","PowerShell","HCL"
        },
        # Web / Backend / Frontend
        "Frameworks & Libs": {
            # Backend & APIs
            "Node.js","Express","NestJS","FastAPI","Django","Flask","Spring Boot","Quarkus","Micronaut","Gin","Fiber",
            # Front-end
            "React","Next.js","Vue","Nuxt.js","Angular","Svelte","SvelteKit",
            # Python data libs
            "Pandas","NumPy","scikit-learn","PyTorch","TensorFlow","XGBoost","LightGBM","CatBoost",
            # ORMs / Data access
            "SQLAlchemy","Alembic","Prisma","TypeORM","Sequelize","Mongoose","Hibernate","JPA",
            # Build/bundlers
            "Vite","Webpack","Rollup","esbuild","Turborepo",
        },
        # Données, Data Eng, MLOps / Orchestration
        "Data & MLOps": {
            "Jupyter","MLflow","Weights & Biases","Airflow","Prefect","Dagster","DVC","Great Expectations",
            "dbt","Apache Spark","Hadoop","Kafka Streams","Beam","Ray",
        },
        # DevOps / Cloud / SRE
        "DevOps & Cloud": {
            "Docker","Docker Compose","Kubernetes","Helm","Kustomize","Terraform","OpenTofu","Terragrunt","Pulumi",
            "Ansible","Packer","Nix","Skaffold","Tilt",
            "GitHub Actions","GitLab CI","Jenkins","CircleCI","Travis CI","Azure Pipelines",
            "ArgoCD","FluxCD",
            "Vault","Consul","Nomad",
            "Prometheus","Grafana","Loki","Tempo","Jaeger","Zipkin","OpenTelemetry",
            "NGINX","Traefik","Caddy",
            "Serverless Framework","AWS SAM","CDK","Crossplane",
            "AWS","GCP","Azure","Firebase","Vercel","Netlify","Cloudflare",
        },
        # Bases de données, caches, messages
        "Bases de données & MQ": {
            "PostgreSQL","MySQL","MariaDB","MongoDB","Redis","SQLite","Elasticsearch","OpenSearch",
            "Cassandra","DynamoDB","Snowflake","BigQuery","Redshift",
            "RabbitMQ","Kafka","NATS","SQS","SNS","Kinesis"
        },
        # Qualité / Tests / Lint
        "Qualité & Tests": {
            "PyTest","unittest","tox","nox","coverage.py",
            "Jest","Vitest","Mocha","Chai","Cypress","Playwright",
            "Prettier","ESLint","TSLint","Stylelint",
            "Black","Ruff","isort","Flake8","Pylint","Mypy","Bandit","Semgrep","Snyk","Trivy","Hadolint","pre-commit",
        },
        # Build & Outillage dev
        "Build & Outillage": {
            "poetry","pip-tools","pipenv","Conda","Makefile","Taskfile","Justfile",
            "Gradle","Maven","Bazel",
            "Yarn","npm","pnpm","Turbo","Nx",
            "OpenAPI","Swagger","Postman","Hoppscotch"
        },
        # Sécurité / Observabilité (spécifique)
        "Sécu & Observabilité": {
            "OpenAPI","Sentry","OpenTelemetry","Falco","Kyverno","OPA","Sigstore","Cosign","Clair",
            "Datadog","New Relic","Elastic APM","Jaeger","Zipkin"
        },
        # Mobile & Desktop
        "Mobile & Desktop": {
            "React Native","Expo","Flutter","Swift","SwiftUI","Kotlin Android","Electron","Tauri"
        },
        # BI / Visualisation
        "BI & Viz": {
            "Power BI","Tableau","Metabase","Superset","Plotly","Matplotlib","Seaborn","Altair","ggplot2"
        },
    }

    # -----------------------------
    # Mappages dépendances → skill
    # -----------------------------

    # Python
    PY_DEP_TO_SKILL: Dict[str, str] = {
        # Data & ML
        "pandas":"Pandas","numpy":"NumPy","scikit-learn":"scikit-learn",
        "torch":"PyTorch","pytorch":"PyTorch","tensorflow":"TensorFlow","keras":"TensorFlow",
        "xgboost":"XGBoost","lightgbm":"LightGBM","catboost":"CatBoost","ray":"Ray",
        # MLOps / orchestration
        "mlflow":"MLflow","wandb":"Weights & Biases","apache-airflow":"Airflow","airflow":"Airflow",
        "prefect":"Prefect","dagster":"Dagster","dvc":"DVC","great-expectations":"Great Expectations","ge":"Great Expectations",
        "dbt":"dbt",
        # Web / APIs
        "fastapi":"FastAPI","uvicorn":"FastAPI","starlette":"FastAPI","pydantic":"FastAPI",
        "django":"Django","djangorestframework":"Django","flask":"Flask","connexion":"OpenAPI",
        "gunicorn":"Python","hypercorn":"Python",
        # Data access / ORMs
        "sqlalchemy":"SQLAlchemy","alembic":"Alembic","psycopg2":"PostgreSQL","asyncpg":"PostgreSQL",
        "pymysql":"MySQL","mysqlclient":"MySQL","pymongo":"MongoDB","redis":"Redis",
        "elasticsearch":"Elasticsearch","opensearch-py":"OpenSearch","kafka-python":"Kafka","confluent-kafka":"Kafka","pika":"RabbitMQ",
        # Cloud SDKs
        "boto3":"AWS","botocore":"AWS","awscli":"AWS",
        "google-cloud-storage":"GCP","google-cloud-bigquery":"BigQuery","google-cloud-pubsub":"GCP",
        "azure-storage-blob":"Azure","azure-identity":"Azure","azure-core":"Azure",
        # Observabilité
        "opentelemetry-api":"OpenTelemetry","opentelemetry-sdk":"OpenTelemetry","sentry-sdk":"Sentry",
        # Tests / Qualité
        "pytest":"PyTest","pytest-cov":"PyTest","tox":"tox","nox":"nox","coverage":"coverage.py",
        "black":"Black","ruff":"Ruff","isort":"isort","flake8":"Flake8","pylint":"Pylint","mypy":"Mypy","bandit":"Bandit","semgrep":"Semgrep",
        "pre-commit":"pre-commit",
        # Tooling / packaging
        "poetry":"poetry","pip-tools":"pip-tools","pipenv":"pipenv","conda":"Conda","setuptools":"Python","nuitka":"Python",
        # Clients HTTP & utilitaires (indices faibles)
        "requests":"Python","httpx":"Python","aiohttp":"Python",
    }

    # JavaScript / TypeScript (npm)
    JS_DEP_TO_SKILL: Dict[str, str] = {
        # Runtimes / tooling
        "typescript":"TypeScript","ts-node":"TypeScript","tsx":"TypeScript",
        # Back-end & APIs
        "express":"Express","nestjs":"NestJS","@nestjs/core":"NestJS","fastify":"Node.js","hapi":"Node.js",
        # Front-end
        "react":"React","next":"Next.js","vue":"Vue","nuxt":"Nuxt.js","@angular/core":"Angular","svelte":"Svelte","@sveltejs/kit":"SvelteKit",
        # State / UI misc
        "redux":"React","zustand":"React","react-query":"React","@tanstack/react-query":"React",
        # ORMs / Data
        "prisma":"Prisma","typeorm":"TypeORM","sequelize":"Sequelize","mongoose":"Mongoose",
        # Build / bundlers / monorepos
        "vite":"Vite","webpack":"Webpack","rollup":"Rollup","esbuild":"esbuild","turbo":"Turborepo","@nrwl/workspace":"Nx","nx":"Nx",
        # Test / qualité
        "jest":"Jest","vitest":"Vitest","mocha":"Mocha","chai":"Chai","cypress":"Cypress","playwright":"Playwright",
        "prettier":"Prettier","eslint":"ESLint","stylelint":"Stylelint","lint-staged":"pre-commit",
        # Observabilité
        "opentelemetry-api":"OpenTelemetry","@sentry/browser":"Sentry","@sentry/node":"Sentry","@sentry/react":"Sentry",
        # Cloud SDKs
        "aws-sdk":"AWS","@aws-sdk/client-s3":"AWS","@aws-sdk/client-dynamodb":"AWS","@aws-cdk/core":"CDK","aws-cdk":"CDK",
        "firebase":"Firebase","firebase-admin":"Firebase","@google-cloud/storage":"GCP","@google-cloud/pubsub":"GCP",
        "@azure/identity":"Azure","@azure/storage-blob":"Azure",
        # GraphQL / API tooling
        "graphql":"GraphQL","apollo-server":"GraphQL","@apollo/server":"GraphQL","apollo-client":"GraphQL","@graphql-codegen/cli":"GraphQL",
        "swagger-ui-express":"OpenAPI","swagger-jsdoc":"OpenAPI","redocly":"OpenAPI",
        # Serverless
        "serverless":"Serverless Framework","@serverless/cli":"Serverless Framework",
        # Realtime / MQ
        "socket.io":"Node.js","kafkajs":"Kafka","amqplib":"RabbitMQ","nats":"NATS",
    }

    # -----------------------------
    # Indices par fichiers → skill
    # -----------------------------
    FILE_HINTS: List[Tuple[str,str,float]] = [
        # Containers & orchestration
        (r"(^|/)Dockerfile$", "Docker", 2.0),
        (r"(^|/)dockerfiles?/.*", "Docker", 1.6),
        (r"(^|/)docker-compose(\\.[a-zA-Z0-9_-]+)?\\.ya?ml$", "Docker Compose", 2.0),
        (r"(^|/)(compose|docker)\\.ya?ml$", "Docker Compose", 1.8),
        (r"\\.(k8s|kubernetes)\\.ya?ml$", "Kubernetes", 1.6),
        (r"(^|/)k8s/.+\\.ya?ml$", "Kubernetes", 2.0),
        (r"(^|/)manifests?/.+\\.ya?ml$", "Kubernetes", 1.6),
        (r"(^|/)kustomization\\.ya?ml$", "Kustomize", 1.8),
        (r"(^|/)charts/.*/Chart\\.ya?ml$", "Helm", 2.0),
        (r"(^|/)charts/.*/values\\.ya?ml$", "Helm", 1.6),
        (r"(^|/)skaffold\\.ya?ml$", "Skaffold", 1.6),
        (r"(^|/)Tiltfile$", "Tilt", 1.4),

        # IaC
        (r"\\.(tf|tfvars)$", "Terraform", 2.0),
        (r"(^|/)tofu\\.(tf|tfvars)$", "OpenTofu", 1.8),
        (r"(^|/)terragrunt\\.hcl$", "Terragrunt", 1.8),
        (r"\\.(bicep)$", "Azure", 1.6),
        (r"(^|/)pulumi\\.(ya?ml|json|ts|py|go)$", "Pulumi", 1.6),
        (r"(^|/)crossplane/.+\\.ya?ml$", "Crossplane", 1.6),

        # CI/CD
        (r"(^|/)\\.github/workflows/.*\\.ya?ml$", "GitHub Actions", 2.2),
        (r"(^|/)Jenkinsfile$", "Jenkins", 2.1),
        (r"(^|/)\\.gitlab-ci\\.ya?ml$", "GitLab CI", 2.1),
        (r"(^|/)\\.circleci/config\\.ya?ml$", "CircleCI", 2.0),
        (r"(^|/)\\.travis\\.ya?ml$", "Travis CI", 1.6),
        (r"(^|/)azure-pipelines\\.ya?ml$", "Azure Pipelines", 2.0),
        (r"(^|/)argocd/.+\\.ya?ml$", "ArgoCD", 1.8),
        (r"(^|/)\\.flux/.+\\.ya?ml$", "FluxCD", 1.8),

        # Python packaging / env
        (r"(^|/)requirements(\\..+)?\\.txt$", "Python", 0.0),
        (r"(^|/)pyproject\\.toml$", "Python", 0.5),
        (r"(^|/)Pipfile(\\.lock)?$", "Python", 0.3),
        (r"(^|/)environment\\.ya?ml$", "Conda", 1.2),
        (r"(^|/)setup\\.(cfg|py)$", "Python", 0.3),
        (r"(^|/)noxfile\\.py$", "nox", 1.0),
        (r"(^|/)tox\\.ini$", "tox", 1.0),

        # JS/TS packaging
        (r"(^|/)package\\.json$", "Node.js", 0.4),
        (r"(^|/)package-lock\\.json$", "Node.js", 0.4),
        (r"(^|/)yarn\\.lock$", "Node.js", 0.4),
        (r"(^|/)pnpm-lock\\.ya?ml$", "Node.js", 0.4),
        (r"(^|/)tsconfig\\.(json|\\.base\\.json)$", "TypeScript", 0.9),

        # Java / JVM
        (r"(^|/)pom\\.xml$", "Java", 1.5),
        (r"(^|/)build\\.gradle(\\.kts)?$", "Java", 1.2),
        (r"(^|/)settings\\.gradle(\\.kts)?$", "Java", 0.8),

        # Go / Rust / C / C++
        (r"(^|/)go\\.mod$", "Go", 1.5),
        (r"(^|/)go\\.sum$", "Go", 0.8),
        (r"(^|/)Cargo\\.toml$", "Rust", 1.5),
        (r"(^|/)Cargo\\.lock$", "Rust", 0.8),
        (r"(^|/)CMakeLists\\.txt$", "C++", 1.0),

        # Databases / BI
        (r"\\.(sql|db|sqlite)$", "SQL", 0.8),
        (r"(^|/)(schema|migrations?)/.*\\.(sql|ya?ml)$", "SQL", 0.8),
        (r"(^|/)dbt_project\\.ya?ml$", "dbt", 1.2),
        (r"(^|/)models/.+\\.sql$", "dbt", 1.0),

        # Security / Lint / Policy
        (r"(^|/)\\.pre-commit-config\\.ya?ml$", "pre-commit", 1.0),
        (r"(^|/)\\.bandit$", "Bandit", 1.0),
        (r"(^|/)semgrep\\.ya?ml$", "Semgrep", 1.0),
        (r"(^|/)\\.hadolint\\.ya?ml$", "Hadolint", 1.0),
        (r"(^|/)\\.tflint\\.hcl$", "Terraform", 0.8),
        (r"(^|/)\\.opa/.*", "OPA", 1.0),
        (r"(^|/)kyverno/.+\\.ya?ml$", "Kyverno", 1.0),

        # Observability
        (r"(^|/)otel-collector\\.ya?ml$", "OpenTelemetry", 1.4),
        (r"(^|/)prometheus(\\.ya?ml|/.*\\.ya?ml)$", "Prometheus", 1.2),
        (r"(^|/)grafana/.*\\.(json|ya?ml)$", "Grafana", 1.2),
        (r"(^|/)loki\\.ya?ml$", "Loki", 1.0),
        (r"(^|/)tempo\\.ya?ml$", "Tempo", 1.0),

        # REST / API / Docs
        (r"(^|/)openapi(\\.ya?ml|\\.json)$", "OpenAPI", 1.2),
        (r"(^|/)swagger\\.(ya?ml|json)$", "OpenAPI", 1.0),

        # Make & tasks
        (r"(^|/)Makefile$", "Makefile", 1.0),
        (r"(^|/)Taskfile\\.ya?ml$", "Taskfile", 1.0),
        (r"(^|/)Justfile$", "Justfile", 1.0),

        # Shell
        (r"\\.(sh|bash)$", "Shell", 0.8),
        (r"(^|/)scripts?/.*\\.(sh|bash)$", "Shell", 0.9),

        # Mobile / Desktop
        (r"(^|/)app\\.json$", "React Native", 0.8),
        (r"(^|/)app\\.config\\.(js|ts)$", "Expo", 0.9),
        (r"(^|/)pubspec\\.ya?ml$", "Flutter", 1.2),
        (r"(^|/)CMakeLists\\.txt$", "C++", 1.0),
        (r"(^|/)package\\.swift$", "Swift", 1.0),

        # Cloud vendor specifics
        (r"(^|/)template\\.yaml$", "AWS SAM", 1.4),
        (r"(^|/)serverless\\.ya?ml$", "Serverless Framework", 1.6),
        (r"(^|/)cdk\\.json$", "CDK", 1.2),
        (r"(^|/)cloudbuild\\.ya?ml$", "GCP", 1.4),
        (r"(^|/)app\\.yaml$", "GCP", 1.0),
        (r"(^|/)firebase\\.(json|rc)$", "Firebase", 1.2),

        # Edge / Hosting
        (r"(^|/)vercel\\.json$", "Vercel", 1.0),
        (r"(^|/)netlify\\.toml$", "Netlify", 1.0),
        (r"(^|/)wrangler\\.toml$", "Cloudflare", 1.0),
    ]

    # -----------------------------
    # Normalisation des noms GitHub → compétence
    # -----------------------------
    @staticmethod
    def map_language(name: str) -> Optional[str]:
        mapping = {
            # Major languages
            "Python": "Python",
            "JavaScript": "JavaScript",
            "TypeScript": "TypeScript",
            "Go": "Go",
            "Rust": "Rust",
            "C": "C",
            "C++": "C++",
            "C#": "C#",
            "Java": "Java",
            "Scala": "Scala",
            "Kotlin": "Kotlin",
            "PHP": "PHP",
            "Ruby": "Ruby",
            "R": "R",
            "Shell": "Shell",
            "PowerShell": "PowerShell",
            # Notebooks
            "Jupyter Notebook": "Jupyter",
            # Web assets
            "HTML": "HTML",
            "CSS": "CSS",
            "SCSS": "CSS",
            "Less": "CSS",
            # Data / Query
            "SQLPL": "SQL",
            "PLpgSQL": "SQL",
            "PLSQL": "SQL",
            "TSQL": "SQL",
            # Infra
            "HCL": "HCL",
            "Nix": "Nix",
            # Other misc often present
            "Makefile": "Makefile",
            "CMake": "C++",
            "Dockerfile": "Docker",
            "TeX": None,
            "Markdown": None,
            "MDX": None,
        }
        return mapping.get(name, None)
