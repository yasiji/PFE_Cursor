"""Authentication routes."""

from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.api_gateway.database import get_db
from services.api_gateway.models import User
from services.api_gateway.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from shared.logging_setup import get_logger
from shared.config import get_config

logger = get_logger(__name__)
config = get_config()

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: str
    password: str
    role: str = "store_manager"
    store_id: int = None


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    role: str
    store_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login endpoint.
    
    For testing, you can create a user first using /register endpoint.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Note: In production, this should be restricted to admin users only.
    """
    if config.environment != "dev" and not config.auth.allow_self_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is disabled in this environment"
        )
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    try:
        hashed_password = get_password_hash(user_data.password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        store_id=user_data.store_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role=new_user.role,
        store_id=new_user.store_id,
        is_active=new_user.is_active
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        store_id=current_user.store_id,
        is_active=current_user.is_active
    )

