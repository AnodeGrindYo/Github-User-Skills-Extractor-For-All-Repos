from __future__ import annotations

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
