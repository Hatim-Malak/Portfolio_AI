from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from config.rate_limiter import limiter
from jose import jwt

from config.database import collection_user_name, collection_blacklist
from datetime import datetime, timezone
from config.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    oauth2_scheme
)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/login")
@limiter.limit("5/minute")
async def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = collection_user_name.find_one({
        "email": form_data.username
    })

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    password_valid = verify_password(
        form_data.password,
        user["passwordHash"]
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token({
        "sub": user["email"]
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me")
async def read_users_me(
    current_user: dict = Depends(get_current_user)
):
    """
    Check if the user is authenticated and return their basic info.
    If the token is invalid or expired, get_current_user will automatically throw a 401 error.
    """
    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "role": current_user.get("role", "user")
    }

@router.post("/logout")
async def logout_user(
    token: str = Depends(oauth2_scheme),
    current_user: dict = Depends(get_current_user)
):
    """
    Log out the user by blacklisting their current token's JTI.
    """
    try:
        # We don't need to verify signature here because get_current_user already did
        payload = jwt.get_unverified_claims(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        if not jti or not exp:
            raise HTTPException(status_code=400, detail="Invalid token structure")
            
        collection_blacklist.insert_one({
            "jti": jti,
            "expiresAt": datetime.fromtimestamp(exp, tz=timezone.utc),
            "blacklisted_on": datetime.now(timezone.utc)
        })
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error processing logout")