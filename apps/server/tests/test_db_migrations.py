from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from app.db.models import Base

SERVER = Path(__file__).resolve().parent.parent


def alembic_config(url: str) -> Config:
    cfg = Config(str(SERVER / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVER / "app" / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_migrations_match_models_and_are_reversible(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    cfg = alembic_config(f"sqlite+aiosqlite:///{db.as_posix()}")
    command.upgrade(cfg, "head")

    engine = sa.create_engine(f"sqlite:///{db.as_posix()}")
    with engine.connect() as conn:
        tables = set(sa.inspect(conn).get_table_names())
        assert {
            "players",
            "accounts",
            "games",
            "game_players",
            "seasons",
            "groups",
            "group_members",
            "challenges",
        } <= tables
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == [], f"models and migrations disagree: {diff}"
    engine.dispose()

    command.downgrade(cfg, "base")
    engine = sa.create_engine(f"sqlite:///{db.as_posix()}")
    with engine.connect() as conn:
        assert set(sa.inspect(conn).get_table_names()) <= {"alembic_version"}
    engine.dispose()


def test_models_can_store_a_finished_game(tmp_path: Path) -> None:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from app.db.models import Game, GamePlayer, Player

    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        player = Player(display_name="Aya", is_guest=False)
        game = Game(
            room_code="ABC234",
            settings={"lives": 3},
            started_at=datetime(2026, 1, 1),
            ended_at=datetime(2026, 1, 1),
        )
        game.players = [
            GamePlayer(
                seat=0,
                player_id=player.id,
                display_name="Aya",
                place=1,
                score=12,
                words=4,
                longest_word="さくら",
            ),
            GamePlayer(seat=1, player_id=None, display_name="Guest", place=2),
        ]
        session.add_all([player, game])
        session.commit()
        stored = session.scalars(sa.select(Game)).one()
        assert stored.settings == {"lives": 3}
        assert [p.place for p in sorted(stored.players, key=lambda p: p.seat)] == [1, 2]
    engine.dispose()
