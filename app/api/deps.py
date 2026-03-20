import uuid

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.core.config import settings
from app.db.session import get_db_session
from app.auth.jwt import decode_token


async def get_db() -> AsyncSession:
    async for session in get_db_session():
        yield session


# No longer need local decode_jwt_token as we use app.auth.jwt.decode_token


async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    """
    Minimal JWT auth dependency.

    Expected header:
      Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = parts[1]
    try:
        payload = decode_token(token, expected_type="access")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    try:
        return str(uuid.UUID(user_id))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token subject") from e


async def get_current_user_id_from_request(
    request: Request,
    authorization: str | None = Header(default=None),
) -> uuid.UUID:
    user_id_str = await get_current_user_id(authorization=authorization)
    user_id = uuid.UUID(user_id_str)
    request.state.user_id = user_id
    return user_id

