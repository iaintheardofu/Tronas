"""
Authentication API endpoints with Azure AD integration.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class UserLogin(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    """User response schema."""
    id: int
    email: str
    full_name: str
    department: Optional[str]
    role: str
    is_active: bool


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Authenticate user and return JWT token.

    For Azure AD SSO, use /auth/azure endpoint instead.
    """
    # Mock authentication - would validate against database
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
    }


@router.get("/azure/login")
async def azure_login():
    """
    Initiate Azure AD SSO login flow.

    Redirects to Microsoft login page.
    """
    return {
        "redirect_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        "message": "Redirect user to this URL to initiate Azure AD login",
    }


@router.post("/azure/callback")
async def azure_callback(code: str):
    """
    Handle Azure AD OAuth callback.

    Exchanges authorization code for tokens.
    """
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": 1,
            "email": "user@city.gov",
            "full_name": "City User",
            "role": "records_liaison",
        },
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current authenticated user information.
    """
    # Would decode token and fetch user
    return {
        "id": 1,
        "email": "maria.garcia@city.gov",
        "full_name": "Maria Garcia",
        "department": "City Secretary",
        "role": "records_liaison",
        "is_active": True,
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token.
    """
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
    }


@router.post("/logout")
async def logout():
    """
    Logout user and invalidate tokens.
    """
    return {
        "message": "Successfully logged out",
    }
