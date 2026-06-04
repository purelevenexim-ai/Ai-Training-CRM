"""
Authentication & Authorization Endpoints
Provides JWT token generation and API key management
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import os

try:
    from database import SessionLocal
    from crm_models import APIKey
    from auth import create_access_token, generate_api_key, verify_access_token, TokenResponse, APIKeyResponse
except ImportError:
    from app.database import SessionLocal
    from app.crm_models import APIKey
    from app.auth import create_access_token, generate_api_key, verify_access_token, TokenResponse, APIKeyResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============= ADMIN ENDPOINTS =============

@router.post("/keys", response_model=APIKeyResponse)
async def create_api_key(
    name: str,
    expires_in_days: int = 365,
    description: str = None,
    db: Session = Depends(get_db)
):
    """
    Create a new API key for programmatic access.
    
    Args:
        name: Human-readable name (e.g. "Mobile App")
        expires_in_days: Days until key expires (default 365)
        description: Optional description
    
    Returns:
        APIKeyResponse with the new key (only shown once)
    """
    # Generate raw key
    raw_key = f"sk_live_{generate_api_key()}"
    
    # Hash it for storage (SHA256)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    # Store in database
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        key_preview=raw_key[:8],
        expires_at=expires_at,
        description=description,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,  # Only returned now
        created_at=api_key.created_at.isoformat(),
        expires_at=expires_at.isoformat() if expires_at else None,
        is_active=True
    )


@router.get("/keys")
async def list_api_keys(db: Session = Depends(get_db)):
    """
    List all API keys (excludes the actual key value).
    
    Returns:
        List of APIKeyResponse without the key value
    """
    keys = db.query(APIKey).filter(APIKey.is_active == True).all()
    
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key=f"{key.key_preview}...",  # Masked
            created_at=key.created_at.isoformat(),
            expires_at=key.expires_at.isoformat() if key.expires_at else None,
            is_active=key.is_active
        )
        for key in keys
    ]


@router.delete("/keys/{key_id}")
async def revoke_api_key(key_id: str, db: Session = Depends(get_db)):
    """
    Revoke an API key (soft delete).
    
    Args:
        key_id: ID of key to revoke
    """
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = False
    db.commit()
    
    return {"status": "revoked", "key_id": key_id}


@router.post("/token", response_model=TokenResponse)
async def get_access_token(
    api_key_value: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Exchange an API key for a JWT access token.
    
    Headers:
        X-API-Key: <api_key_value>
    
    Returns:
        TokenResponse with JWT access token
    """
    # Hash the provided key
    key_hash = hashlib.sha256(api_key_value.encode()).hexdigest()
    
    # Look up in database
    api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check expiration
    if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
        raise HTTPException(status_code=401, detail="API key expired")
    
    # Update last_used_at
    api_key.last_used_at = datetime.utcnow()
    db.commit()
    
    # Generate JWT token (24 hour expiration)
    token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": api_key.id, "scope": api_key.scope},
        expires_delta=token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=int(token_expires.total_seconds())
    )


@router.post("/verify")
async def verify_token(authorization: str = Header(...)):
    """
    Verify a JWT token without consuming it.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        Token claims if valid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format"
        )
    
    token = parts[1]
    payload = verify_access_token(token)
    
    return {"valid": True, "payload": payload}


# ============= HEALTH CHECK =============

@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "service": "auth"}
