from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


def test_migration_upgrade_and_downgrade(tmp_path: Path, monkeypatch: object) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)  # type: ignore[attr-defined]
    get_settings.cache_clear()

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert {
        "alembic_version",
        "trends",
        "trend_aliases",
        "collection_runs",
        "observations",
        "search_trend_observations",
    }.issubset(
        set(inspect(engine).get_table_names())
    )

    command.downgrade(config, "base")
    assert "trends" not in inspect(engine).get_table_names()
    assert "trend_aliases" not in inspect(engine).get_table_names()
    assert "collection_runs" not in inspect(engine).get_table_names()
    assert "observations" not in inspect(engine).get_table_names()
    assert "search_trend_observations" not in inspect(engine).get_table_names()
    engine.dispose()
    get_settings.cache_clear()
