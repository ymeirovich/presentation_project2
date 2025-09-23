"""Authentication and authorization utilities for PresGen-Assess API."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from src.common.config import settings

logger = logging.getLogger(__name__)

# Security configuration
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = getattr(settings, 'jwt_secret_key', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class AuthenticationError(Exception):
    """Custom authentication error."""
    pass


class AuthorizationError(Exception):
    """Custom authorization error."""
    pass


# User roles and permissions
ROLE_PERMISSIONS = {
    "admin": [
        "assessments:create",
        "assessments:read",
        "assessments:update",
        "assessments:delete",
        "engine:manage",
        "llm:manage",
        "gap-analysis:manage",
        "presentations:manage",
        "users:manage"
    ],
    "educator": [
        "assessments:create",
        "assessments:read",
        "assessments:update",
        "engine:use",
        "llm:use",
        "gap-analysis:use",
        "presentations:create"
    ],
    "student": [
        "assessments:read",
        "engine:use",
        "gap-analysis:view",
        "presentations:view"
    ],
    "api_client": [
        "assessments:create",
        "assessments:read",
        "engine:use",
        "llm:use",
        "gap-analysis:use",
        "presentations:create"
    ]
}


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


def verify_token(token: str) -> Dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise AuthenticationError("Invalid token: missing subject")

        return payload

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")

    except jwt.JWTError:
        raise AuthenticationError("Invalid token")


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Get current authenticated user from JWT token."""
    try:
        token = credentials.credentials
        payload = verify_token(token)

        # In production, you would fetch user details from database
        user_data = {
            "username": payload.get("sub"),
            "user_id": payload.get("user_id"),
            "role": payload.get("role", "student"),
            "permissions": ROLE_PERMISSIONS.get(payload.get("role", "student"), [])
        }

        logger.info(f"🔐 User authenticated: {user_data['username']} (role: {user_data['role']})")
        return user_data

    except AuthenticationError as e:
        logger.warning(f"🔒 Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_admin_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Require admin role for access."""
    if current_user["role"] != "admin":
        logger.warning(f"🚫 Admin access denied for user: {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def get_educator_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Require educator or admin role for access."""
    if current_user["role"] not in ["educator", "admin"]:
        logger.warning(f"🚫 Educator access denied for user: {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Educator access required"
        )

    return current_user


def require_permission(permission: str):
    """Decorator factory for permission-based access control."""
    def permission_checker(current_user: Dict = Depends(get_current_user)) -> Dict:
        if permission not in current_user["permissions"]:
            logger.warning(f"🚫 Permission denied: {permission} for user: {current_user['username']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )

        return current_user

    return permission_checker


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests = {}

    def is_allowed(self, client_id: str, limit: int = 100, window_minutes: int = 15) -> bool:
        """Check if request is within rate limit."""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)

        # Clean old entries
        self.requests = {
            key: timestamps for key, timestamps in self.requests.items()
            if any(ts > window_start for ts in timestamps)
        }

        # Get recent requests for this client
        if client_id not in self.requests:
            self.requests[client_id] = []

        recent_requests = [
            ts for ts in self.requests[client_id]
            if ts > window_start
        ]

        # Check rate limit
        if len(recent_requests) >= limit:
            logger.warning(f"🚦 Rate limit exceeded for client: {client_id}")
            return False

        # Add current request
        self.requests[client_id] = recent_requests + [now]
        return True

    def get_stats(self, client_id: str) -> Dict:
        """Get rate limiting stats for client."""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=15)

        recent_requests = [
            ts for ts in self.requests.get(client_id, [])
            if ts > window_start
        ]

        return {
            "client_id": client_id,
            "requests_in_window": len(recent_requests),
            "window_minutes": 15,
            "remaining_capacity": max(0, 100 - len(recent_requests))
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(client_id: str, limit: int = 100) -> None:
    """Check rate limit for client."""
    if not rate_limiter.is_allowed(client_id, limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "900"}  # 15 minutes
        )


# Optional authentication for development/testing
async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def create_demo_token(username: str = "demo_user", role: str = "educator") -> str:
    """Create a demo token for testing purposes."""
    token_data = {
        "sub": username,
        "user_id": f"{username}_id",
        "role": role
    }

    return create_access_token(
        data=token_data,
        expires_delta=timedelta(hours=24)
    )