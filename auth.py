"""
JWT Authentication for Pureleven CRM API
Provides secure API key and token-based authentication
"""

import os
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ============= PYDANTIC MODELS =============

class APIKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = 365

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: str  # Only shown once on creation
    created_at: str
    expires_at: Optional[str] = None
    is_active: bool = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in_seconds: int

# ============= TOKEN GENERATION & VALIDATION =============

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Claims to encode (e.g., {"sub": "user_id"})
        expires_delta: Custom expiration time
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT access token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token data
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


def generate_api_key() -> str:
    """
    Generate a secure random API key
    
    Returns:
        Random 32-byte hex string
    """
    return secrets.token_urlsafe(32)


# ============= AUTH MIDDLEWARE =============

async def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency to verify API key from Authorization header
    
    Expected format: Authorization: Bearer <token>
    
    Args:
        authorization: Authorization header value
    
    Returns:
        Decoded token data
    
    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <token>"
        )
    
    token = parts[1]
    return verify_access_token(token)


async def optional_auth(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency for optional authentication
    Returns None if no auth provided, decoded token if provided
    """
    if not authorization:
        return None
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        return verify_access_token(parts[1])
    except HTTPException:
        return None


# ============= HELPER FUNCTIONS =============

def is_token_expired(exp_timestamp: float) -> bool:
    """Check if token expiration timestamp is in the past"""
    return datetime.now(timezone.utc).timestamp() > exp_timestamp


def get_token_expiry_time(token: str) -> Optional[datetime]:
    """Get the expiration time of a token without validating signature"""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None
    except:
        return None
