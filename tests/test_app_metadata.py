from app.main import app
from app.core.config import CORS_ORIGINS


def test_signalforge_metadata_and_safe_debug_default():
    assert app.title == "SignalForge"
    assert app.version == "1.0.0"
    assert app.debug is False
    assert "http://localhost:5173" in CORS_ORIGINS
