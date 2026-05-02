from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.runtime import get_db_session
from app.domains.auth.schemas import LoginRequest, LoginResponse, RegisterRequest
from app.domains.auth.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
)
from app.domains.users.models import User
from app.domains.users.schemas import UserProfile
from app.domains.users.service import get_user_by_email, get_user_by_username

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db_session),
) -> UserProfile:
    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already in use.",
        )

    if get_user_by_username(db, payload.username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already in use.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        display_name=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username is already in use.",
        ) from exc

    db.refresh(user)
    return UserProfile.model_validate(user)


@router.post("/login", response_model=LoginResponse)
def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    access_token = create_access_token(str(user.id), settings)
    return LoginResponse(
        access_token=access_token,
        user=UserProfile.model_validate(user),
    )


@router.get("/me", response_model=UserProfile)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    return UserProfile.model_validate(current_user)
