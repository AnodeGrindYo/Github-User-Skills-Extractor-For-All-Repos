import json
from types import SimpleNamespace
from cvskills_extractor.analyzer import RepoAnalyzer
from cvskills_extractor.github_http import GitHubHTTP

class FakeGH(GitHubHTTP):
    def __init__(self):
        pass
    def _req(self, url: str):
        if url.endswith('/languages'):
            # Strong Python signal; HTML/CSS should be ignored by map_language
            return {'Python': 9000, 'HTML': 1000, 'CSS': 500}
        # tree fallback
        if '/git/trees/' in url:
            return {'tree': [{'path': 'Dockerfile', 'type': 'blob'},
                             {'path': 'k8s/deploy.yaml', 'type': 'blob'},
                             {'path': 'charts/app/Chart.yaml', 'type': 'blob'},
                             {'path': 'package.json', 'type': 'blob'},
                             {'path': 'pyproject.toml', 'type': 'blob'}]}
        return {}

    def repo_tree(self, owner, repo, ref):
        return self._req(f'https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1')

    def get_file(self, owner, repo, path, ref):
        if path == 'package.json':
            return json.dumps({
                'dependencies': {'react': '^18.0.0', 'typescript': '^5.0.0'}
            })
        if path == 'pyproject.toml':
            return '''[project]
dependencies = ["fastapi", "pandas", "pytest"]
'''
        if path.endswith('.yaml'):
            return 'apiVersion: v1\nkind: Deployment\nmetadata: {}\n'
        return None

def test_analyzer_detects_languages_and_hints():
    gh = FakeGH()
    repo_meta = {'name': 'demo', 'default_branch': 'main', 'stargazers_count': 0, 'forks_count': 0}
    ra = RepoAnalyzer(gh, 'user', repo_meta)
    idx = ra.analyze()
    agg = idx.aggregate()
    skills = {s for s, *_ in agg}
    # Language + file hints + deps
    assert 'Python' in skills
    assert 'Docker' in skills
    assert 'Kubernetes' in skills
    assert 'Helm' in skills
    assert 'React' in skills
    assert 'TypeScript' in skills
    assert 'FastAPI' in skills
    assert 'Pandas' in skills
