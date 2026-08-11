from app.main import app


def test_signalforge_metadata_and_safe_debug_default():
    assert app.title == "SignalForge"
    assert app.version == "1.0.0"
    assert app.debug is False
