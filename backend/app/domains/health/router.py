from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.runtime import get_db_session
from app.domains.health.schemas import HealthResponse, ServiceHealth

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def read_health(db: Session = Depends(get_db_session)) -> JSONResponse:
    api_health = ServiceHealth(status="ok", ready=True)

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        payload = HealthResponse(
            status="degraded",
            api=api_health,
            database=ServiceHealth(status="error", ready=False),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    payload = HealthResponse(
        status="ok",
        api=api_health,
        database=ServiceHealth(status="ok", ready=True),
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload.model_dump())
