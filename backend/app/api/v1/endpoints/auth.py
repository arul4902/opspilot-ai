from typing import Any
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user
from backend.app.schemas.auth import (
    UserRegister,
    UserResponse,
    LoginRequest,
    Token
)
from backend.app.services.auth_service import AuthService
from backend.app.models.models import User

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Register a new user (customer, operations agent, or admin).
    """
    client_ip = request.client.host if request.client else None
    auth_service = AuthService(db)
    return auth_service.register(user_in, ip_address=client_ip)


@router.post("/login", response_model=Token)
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Login with JSON body email and password to retrieve a JWT access token.
    """
    client_ip = request.client.host if request.client else None
    auth_service = AuthService(db)
    return auth_service.authenticate(login_data, ip_address=client_ip)


@router.post("/token", response_model=Token, include_in_schema=False)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, for Swagger UI 'Authorize' button.
    """
    client_ip = request.client.host if request.client else None
    auth_service = AuthService(db)
    login_req = LoginRequest(email=form_data.username, password=form_data.password)
    return auth_service.authenticate(login_req, ip_address=client_ip)


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Retrieve profile details for the currently authenticated user.
    """
    return current_user

