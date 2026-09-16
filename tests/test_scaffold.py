import os
def test_spec_exists():
    assert os.path.exists("docs/superpowers/specs/2026-09-16-beau-superagent-design.md")
def test_openrouter_config_importable():
    import openrouter_config
    assert hasattr(openrouter_config, "OPENROUTER_MODEL")
def test_beau_pkg_exists():
    import beau
    assert True
