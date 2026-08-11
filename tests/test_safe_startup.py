from pathlib import Path


def test_application_startup_never_drops_database_tables():
    main_source = (Path(__file__).parents[1] / "app" / "main.py").read_text()

    assert "drop_all" not in main_source
    assert "create_all" not in main_source
