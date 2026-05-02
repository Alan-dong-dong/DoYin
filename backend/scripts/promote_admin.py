from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.base import Base, load_model_metadata
from app.db.session import create_engine_from_url, create_session_factory
from app.domains.users.service import (
    get_user_by_email,
    get_user_by_username,
    set_user_admin_status,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Grant admin access to an existing local DoYin user account. "
            "This is intended for local development bootstrap only."
        )
    )
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--email", help="Promote the user with this email address.")
    target_group.add_argument("--username", help="Promote the user with this username.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    engine = create_engine_from_url(settings.resolved_database_url)
    load_model_metadata()
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)
    session = session_factory()

    try:
        user = (
            get_user_by_email(session, args.email)
            if args.email
            else get_user_by_username(session, args.username)
        )
        if user is None:
            target = args.email or args.username
            print(f"User not found: {target}", file=sys.stderr)
            return 1

        set_user_admin_status(session, user, is_admin=True)
        session.commit()
        print(f"Granted admin access to {user.email} (@{user.username}).")
        return 0
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
