"""数据库会话：默认 SQLite，可切换 MySQL。"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _resolve_url(url: str) -> str:
    if url.startswith("sqlite"):
        # 确保目录存在
        if ":///" in url:
            raw = url.split(":///", 1)[1]
            path = Path(raw)
            if not path.is_absolute():
                path = (Path.cwd() / path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{path.as_posix()}"
    return url


settings = get_settings()
# 开发默认使用本地 SQLite，避免强依赖 MySQL
_db_url = settings.database_url
if "mysql" in _db_url and "password@127.0.0.1" in _db_url:
    _db_url = "sqlite:///./data/competition_agent.db"

DATABASE_URL = _resolve_url(_db_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)

if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
