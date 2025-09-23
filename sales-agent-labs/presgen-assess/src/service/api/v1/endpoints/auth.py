"""Authentication API endpoints."""

import logging
from datetime import timedelta
from typing import Dict

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from src.service.auth import (
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
    create_demo_token,
    rate_limiter,
    ROLE_PERMISSIONS
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    expires_in: int
    user_info: Dict


class UserInfoResponse(BaseModel):
    """User info response model."""
    username: str
    user_id: str
    role: str
    permissions: list


class DemoTokenRequest(BaseModel):
    """Demo token request model."""
    username: str = Field(default="demo_user", description="Demo username")
    role: str = Field(default="educator", description="Demo user role")


class RateLimitStatsResponse(BaseModel):
    """Rate limit statistics response model."""
    client_id: str
    requests_in_window: int
    window_minutes: int
    remaining_capacity: int


# Mock user database (In production, use a real database)
MOCK_USERS = {
    "admin": {
        "username": "admin",
        "user_id": "admin_001",
        "hashed_password": get_password_hash("admin123"),
        "role": "admin"
    },
    "educator": {
        "username": "educator",
        "user_id": "educator_001",
        "hashed_password": get_password_hash("educator123"),
        "role": "educator"
    },
    "student": {
        "username": "student",
        "user_id": "student_001",
        "hashed_password": get_password_hash("student123"),
        "role": "student"
    },
    "demo_user": {
        "username": "demo_user",
        "user_id": "demo_001",
        "hashed_password": get_password_hash("demo123"),
        "role": "educator"
    }
}


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest) -> TokenResponse:
    """
    Authenticate user and return access token.

    Validates user credentials and returns a JWT access token
    for authenticated API access.
    """
    try:
        logger.info(f"🔐 Login attempt for user: {credentials.username}")

        # Get user from mock database
        user_data = MOCK_USERS.get(credentials.username)
        if not user_data:
            logger.warning(f"🔒 Login failed: User not found - {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Verify password
        if not verify_password(credentials.password, user_data["hashed_password"]):
            logger.warning(f"🔒 Login failed: Invalid password - {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Create access token
        access_token_expires = timedelta(minutes=30)
        token_data = {
            "sub": user_data["username"],
            "user_id": user_data["user_id"],
            "role": user_data["role"]
        }

        access_token = create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )

        logger.info(f"✅ Login successful for user: {credentials.username}")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user_info={
                "username": user_data["username"],
                "user_id": user_data["user_id"],
                "role": user_data["role"],
                "permissions": ROLE_PERMISSIONS.get(user_data["role"], [])
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to internal error"
        )


@router.post("/demo-token", response_model=TokenResponse)
async def create_demo_access_token(request: DemoTokenRequest) -> TokenResponse:
    """
    Create a demo token for testing purposes.

    Generates a demo token without password validation
    for development and testing scenarios.
    """
    try:
        logger.info(f"🔧 Creating demo token for: {request.username} (role: {request.role})")

        # Validate role
        if request.role not in ROLE_PERMISSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Available roles: {list(ROLE_PERMISSIONS.keys())}"
            )

        # Create demo token
        demo_token = create_demo_token(username=request.username, role=request.role)

        return TokenResponse(
            access_token=demo_token,
            token_type="bearer",
            expires_in=86400,  # 24 hours for demo
            user_info={
                "username": request.username,
                "user_id": f"{request.username}_id",
                "role": request.role,
                "permissions": ROLE_PERMISSIONS.get(request.role, [])
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Demo token creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Demo token creation failed"
        )


@router.get("/me", response_model=UserInfoResponse)
async def get_user_info(current_user: Dict = Depends(get_current_user)) -> UserInfoResponse:
    """
    Get current user information.

    Returns detailed information about the currently
    authenticated user including permissions.
    """
    try:
        return UserInfoResponse(
            username=current_user["username"],
            user_id=current_user["user_id"],
            role=current_user["role"],
            permissions=current_user["permissions"]
        )

    except Exception as e:
        logger.error(f"❌ Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


@router.get("/rate-limit/stats", response_model=RateLimitStatsResponse)
async def get_rate_limit_stats(client_id: str = "current") -> RateLimitStatsResponse:
    """
    Get rate limiting statistics for a client.

    Returns current rate limit usage and remaining capacity
    for monitoring and debugging purposes.
    """
    try:
        # If client_id is "current", use a default identifier
        if client_id == "current":
            client_id = "ip:demo_client"

        stats = rate_limiter.get_stats(client_id)

        return RateLimitStatsResponse(
            client_id=stats["client_id"],
            requests_in_window=stats["requests_in_window"],
            window_minutes=stats["window_minutes"],
            remaining_capacity=stats["remaining_capacity"]
        )

    except Exception as e:
        logger.error(f"❌ Failed to get rate limit stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit statistics"
        )


@router.get("/roles")
async def get_available_roles() -> Dict:
    """
    Get available user roles and their permissions.

    Returns information about all available user roles
    and their associated permissions for reference.
    """
    try:
        return {
            "roles": ROLE_PERMISSIONS,
            "role_descriptions": {
                "admin": "Full system access including user management",
                "educator": "Create and manage assessments and presentations",
                "student": "Take assessments and view presentations",
                "api_client": "Programmatic access to core services"
            }
        }

    except Exception as e:
        logger.error(f"❌ Failed to get roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve role information"
        )


@router.post("/logout")
async def logout(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Logout current user.

    In a JWT-based system, logout is handled client-side
    by discarding the token. This endpoint provides a
    standardized logout confirmation.
    """
    try:
        logger.info(f"👋 User logged out: {current_user['username']}")

        return {
            "message": "Successfully logged out",
            "username": current_user["username"],
            "timestamp": "2024-01-01T00:00:00Z"
        }

    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )