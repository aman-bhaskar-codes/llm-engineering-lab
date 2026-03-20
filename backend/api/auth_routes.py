import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.deps import get_db, get_current_user_id
from auth.jwt import create_access_token, create_refresh_token, decode_token
from auth.password import hash_password, verify_password
from db.models.user import User

router = APIRouter(tags=["auth"])

class UserSignup(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID

class RefreshRequest(BaseModel):
    refresh_token: str

class UserProfile(BaseModel):
    id: uuid.UUID
    email: str
    is_verified: bool
    created_at: Any

@router.post("/auth/signup", response_model=TokenResponse)
async def signup(payload: UserSignup, db: AsyncSession = Depends(get_db)):
    q = select(User).where(User.email == payload.email)
    res = await db.execute(q)
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id
    )

@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    q = select(User).where(User.email == payload.email)
    res = await db.execute(q)
    user = res.scalars().first()

    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        # Fallback for old users created without password (if email matches but no hash)
        if user and not user.password_hash:
            # For this demo/migration, we let them login once and maybe set a password later.
            # But according to plan: "require a password for new signups".
            # For existing ones, we can just allow login if password is correct? 
            # No, if there is no hash, verify_password will fail.
            # Let's just say "Invalid credentials" for safety unless we want a specific migration path.
            pass
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id
    )

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        token_data = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = token_data.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
        access_token = create_access_token(user_id)
        # Optional: rotate refresh token
        new_refresh_token = create_refresh_token(user_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            user_id=uuid.UUID(user_id)
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

@router.get("/me", response_model=UserProfile)
async def get_me(
    user_id_str: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    user_id = uuid.UUID(user_id_str)
    q = select(User).where(User.id == user_id)
    res = await db.execute(q)
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
