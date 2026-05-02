from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def load_model_metadata() -> None:
    from app.domains.users import models  # noqa: F401
    from app.domains.videos import models  # noqa: F401
