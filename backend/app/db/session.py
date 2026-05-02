from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker


def create_engine_from_url(database_url: str) -> Engine:
    if not database_url:
        raise ValueError("DATABASE_URL is not configured.")

    connect_args: dict[str, int] = {}
    if database_url.startswith("postgresql+psycopg://"):
        connect_args["connect_timeout"] = 3

    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
