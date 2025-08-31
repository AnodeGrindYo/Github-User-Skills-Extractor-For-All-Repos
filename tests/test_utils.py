import os
import re
from cvskills_extractor.utils import is_excluded, compile_repo_patterns_from_env

def test_is_excluded_dirs():
    assert is_excluded('project/node_modules/pkg/index.js')
    assert is_excluded('project/.venv/lib/site-packages/x.py')
    assert is_excluded('project/vendor/jquery.js')
    assert not is_excluded('project/src/app/main.py')

def test_compile_repo_patterns_from_env(monkeypatch):
    monkeypatch.setenv('EXCLUDE_REPOS', '^fork-.*, (demo|playground)$')
    pats = compile_repo_patterns_from_env('EXCLUDE_REPOS')
    assert len(pats) == 2
    assert any(re.compile('^fork-.*', re.I).pattern == p.pattern for p in pats)
