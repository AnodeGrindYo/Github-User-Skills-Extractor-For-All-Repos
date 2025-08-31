from cvskills_extractor.evidence import SkillIndex

def test_skillindex_caps_and_dedup():
    idx = SkillIndex()
    # Add multiple evidences for same (skill,repo) to hit cap and dedup
    idx.add('Jupyter', 'repo1', 1.0, 'Notebook 1')
    idx.add('Jupyter', 'repo1', 1.0, 'Notebook 2')
    idx.add('Jupyter', 'repo1', 1.0, 'Notebook 3')  # should be capped at 2.0 per repo
    idx.add('Python', 'repo1', 10.0, 'Lang')  # default cap 5.0
    # Duplicate reason should be ignored
    idx.add('Python', 'repo1', 1.0, 'Lang')
    agg = idx.aggregate()
    d = {s: (sc, r) for s, sc, r, _ in agg}
    assert d['Jupyter'][0] <= 2.01
    assert d['Python'][0] <= 5.01
    # repos distincts should be 1 for both
    assert d['Jupyter'][1] == 1 and d['Python'][1] == 1
