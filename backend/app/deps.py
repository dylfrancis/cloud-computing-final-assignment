from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


async def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


async def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    email = payload.get("sub")
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return email
