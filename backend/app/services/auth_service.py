from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import LoginRequest, UserRegister, Token
from backend.app.security.passwords import verify_password
from backend.app.security.jwt import create_access_token
from backend.app.services.audit_service import AuditService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register(self, user_in: UserRegister, ip_address: Optional[str] = None) -> User:
        existing = self.user_repo.get_by_email(user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )
        new_user = self.user_repo.create(user_in)
        AuditService.log_action(
            db=self.db,
            action="USER_REGISTERED",
            entity_type="user",
            entity_id=str(new_user.id),
            user_id=new_user.id,
            details={"email": new_user.email, "role": new_user.role},
            ip_address=ip_address
        )
        return new_user

    def authenticate(self, login_data: LoginRequest, ip_address: Optional[str] = None) -> Token:
        user = self.user_repo.get_by_email(login_data.email)
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account."
            )

        token = create_access_token(subject=str(user.id), role=user.role)
        AuditService.log_action(
            db=self.db,
            action="USER_LOGIN_SUCCESS",
            entity_type="user",
            entity_id=str(user.id),
            user_id=user.id,
            details={"email": user.email, "role": user.role},
            ip_address=ip_address
        )
        return Token(
            access_token=token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
        )

