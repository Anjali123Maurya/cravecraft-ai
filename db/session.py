
"""Creates the SQLite engine and the Store used by the app."""
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.config import get_settings
from db.models import Base
from db.repositories import Store


def make_store(url: str) -> Store:
    """Build a Store for any database URL ('sqlite://' = in-memory, for tests)."""
    kwargs = {"poolclass": StaticPool} if url in ("sqlite://", "sqlite:///:memory:") else {}
    engine = create_engine(url, connect_args={"check_same_thread": False}, **kwargs)
    Base.metadata.create_all(engine)
    return Store(sessionmaker(engine, expire_on_commit=False))


@lru_cache
def get_store() -> Store:
    path = get_settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return make_store(f"sqlite:///{path.as_posix()}")
