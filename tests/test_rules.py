from cvskills_extractor.rules import SkillRules

def test_py_dep_to_skill_core():
    m = SkillRules.PY_DEP_TO_SKILL
    assert m.get('fastapi') == 'FastAPI'
    assert m.get('pytest') in {'PyTest','pytest-cov','PyTest'}  # allow variants
    assert m.get('pandas') == 'Pandas'

def test_js_dep_to_skill_core():
    m = SkillRules.JS_DEP_TO_SKILL
    assert m.get('react') == 'React'
    assert m.get('next') == 'Next.js'
