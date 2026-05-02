from typing import Literal

from pydantic import BaseModel


class ServiceHealth(BaseModel):
    status: Literal["ok", "error"]
    ready: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    api: ServiceHealth
    database: ServiceHealth

