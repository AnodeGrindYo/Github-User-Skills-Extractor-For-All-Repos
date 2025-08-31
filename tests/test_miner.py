import os, json
from cvskills_extractor.miner import PortfolioMiner
from cvskills_extractor.github_http import GitHubHTTP
from cvskills_extractor.evidence import SkillIndex, Evidence

class FakeGH(GitHubHTTP):
    def __init__(self, username, token):
        self.username = username
        self.token = token
    def list_repos(self, include_private=True, per_page=100):
        return [
            {'name':'r1','owner':{'login':self.username}, 'fork': False, 'archived': False, 'default_branch':'main'},
            {'name':'r2','owner':{'login':self.username}, 'fork': False, 'archived': False, 'default_branch':'main'}
        ]

# Monkeypatch within test to avoid touching source files
def test_miner_generates_outputs(tmp_path, monkeypatch):
    def fake_init(self, username, token, exclude_repo_patterns=None):
        self.gh = FakeGH(username, token)
        self.username = username
        self.exclude_repo_patterns = exclude_repo_patterns or []

    def fake_analyze(self):
        idx = SkillIndex()
        idx.add('Python','r1',1.0,'test')
        idx.add('Docker','r2',1.0,'test')
        return idx

    monkeypatch.setattr('cvskills_extractor.miner.PortfolioMiner.__init__', fake_init, raising=False)
    monkeypatch.setattr('cvskills_extractor.analyzer.RepoAnalyzer.analyze', fake_analyze, raising=True)

    # run in tmp dir to capture outputs
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        pm = PortfolioMiner('u','t',[])
        out = pm.run()
        assert os.path.exists('cv_skills.md')
        assert os.path.exists('skills.json')
        data = json.load(open('skills.json','r',encoding='utf-8'))
        assert 'generated_at' in data and 'skills' in data
        assert any(s['skill']=='Python' for s in data['skills'])
    finally:
        os.chdir(cwd)
