from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from db.db_helper import db_helper
from jwt.jwt_handler import verify_token
from models.user_model import User
from .crud import get_user_by_id

security = HTTPBearer()

async def get_db() -> AsyncSession:
    async for session in db_helper.session_dependency():
        yield session

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = await get_user_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None 