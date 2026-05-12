from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False; PostgreSQL does not
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine_kwargs = {"connect_args": connect_args}
if not settings.database_url.startswith("sqlite"):
    # Long crew runs + frontend polling were exhausting the default 5+10 pool
    # and silently dropping per-task callbacks. Bigger pool, ping before use
    # to drop dead idle connections, recycle every 30 min to stay ahead of
    # any server-side idle timeout.
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    })

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
