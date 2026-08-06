"""Authentication endpoints: register, login, refresh, profile."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut, UserUpdate

router = APIRouter(prefix="/auth", tags=["authentication"])


def _tokens(user: User) -> TokenResponse:
    access = create_access_token(user.id, extra={"role": user.role})
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=7200)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        organization=payload.organization,
        hashed_password=hash_password(payload.password),
        role="researcher",
    )
    db.add(user)
    db.add(AuditLog(user_id=user.id, action="register", resource_type="user"))
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    db.add(AuditLog(user_id=user.id, action="login", resource_type="user"))
    db.commit()
    return _tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    decoded = decode_token(payload.refresh_token, expected_type="refresh")
    if decoded is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.get(User, decoded.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.organization is not None:
        user.organization = payload.organization
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/change-password")
def change_password(payload: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if not verify_password(payload.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.add(AuditLog(user_id=user.id, action="change_password", resource_type="user"))
    db.commit()
    return {"message": "Password updated"}
