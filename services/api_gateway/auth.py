"""Authentication and authorization utilities."""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from services.api_gateway.database import get_db
from services.api_gateway.models import User
from shared.config import get_config
from shared.logging_setup import get_logger

logger = get_logger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# JWT settings
config = get_config()
SECRET_KEY = config.auth.jwt_secret_key
ALGORITHM = config.auth.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = config.auth.access_token_expire_minutes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        # Ensure password is bytes
        password_bytes = plain_password.encode('utf-8')
        # Truncate if longer than 72 bytes (bcrypt limit)
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Handle hashed_password - it might be bytes or string
        if isinstance(hashed_password, bytes):
            hashed_bytes = hashed_password
        else:
            # If it's a string, it should already be a bcrypt hash string
            # bcrypt hashes start with $2b$ or $2a$ or $2y$
            hashed_bytes = hashed_password.encode('utf-8')
        
        # Verify password
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    try:
        # Ensure password is bytes
        password_bytes = password.encode('utf-8')
        # Truncate if longer than 72 bytes (bcrypt limit)
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def require_role(allowed_roles: list[str]):
    """Dependency factory for role-based access control."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of these roles: {allowed_roles}"
            )
        return current_user
    return role_checker

