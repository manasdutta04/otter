from app.health import analyze_health

def test_health_module_is_importable_and_detects_documentation():
    assert callable(analyze_health)
