from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    display_name: str
    avatar_url: str | None
    is_admin: bool
    created_at: datetime
    updated_at: datetime
