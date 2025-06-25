from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime, timedelta

from models.user_model import User
from schemas.user_schemas import UserCreate, UserProfile
from jwt.jwt_handler import get_password_hash, verify_password, create_reset_token, verify_reset_token



async def create_user(db: AsyncSession, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


async def update_user_password(db: AsyncSession, user_id: int, new_password: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    user.password = get_password_hash(new_password)
    await db.commit()
    return True


async def reset_user_password(db: AsyncSession, email: str, new_password: str) -> bool:
    user = await get_user_by_email(db, email)
    if not user:
        return False
    
    user.password = get_password_hash(new_password)
    await db.commit()
    return True


async def get_user_profile(db: AsyncSession, user_id: int) -> Optional[UserProfile]:
    from models.url_model import URL 
    
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    urls_count_result = await db.execute(
        select(func.count(URL.id)).where(URL.owner_id == user_id)
    )
    urls_count = urls_count_result.scalar() or 0
    
    total_clicks_result = await db.execute(
        select(func.sum(URL.click_count)).where(URL.owner_id == user_id)
    )
    total_clicks = total_clicks_result.scalar() or 0
    
    return UserProfile(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        urls_count=urls_count,
        total_clicks=total_clicks
    )


async def update_user_profile(db: AsyncSession, user_id: int, username: str = None) -> Optional[User]:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    if username:
        existing_user = await get_user_by_username(db, username)
        if existing_user and existing_user.id != user_id:
            return None
        user.username = username
    
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True


async def register_user_with_validation(db: AsyncSession, user_data: UserCreate) -> tuple[Optional[User], str]:
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        return None, "Email already registered"
    
    existing_username = await get_user_by_username(db, user_data.username)
    if existing_username:
        return None, "Username already taken"
    
    try:
        user = await create_user(db, user_data)
        return user, "User created successfully"
    except Exception as e:
        return None, f"Could not create user: {str(e)}"


async def login_user_with_validation(db: AsyncSession, email: str, password: str) -> tuple[Optional[User], str]:
    user = await authenticate_user(db, email, password)
    if not user:
        return None, "Incorrect email or password"
    
    return user, "Login successful"


async def change_user_password_with_validation(
    db: AsyncSession, 
    user_id: int, 
    current_password: str, 
    new_password: str
) -> tuple[bool, str]:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False, "User not found"
    
    if not verify_password(current_password, user.password):
        return False, "Current password is incorrect"
    
    success = await update_user_password(db, user_id, new_password)
    if not success:
        return False, "Could not update password"
    
    return True, "Password changed successfully"


async def initiate_password_reset(db: AsyncSession, email: str) -> tuple[bool, str, Optional[str]]:
    user = await get_user_by_email(db, email)

    message = "If email exists, password reset instructions have been sent"
    
    if user:
        reset_token = create_reset_token(user.email)
        return True, message, reset_token
    
    return True, message, None


async def complete_password_reset(db: AsyncSession, token: str, new_password: str) -> tuple[bool, str]:
    email = verify_reset_token(token)
    if not email:
        return False, "Invalid or expired reset token"
    
    success = await reset_user_password(db, email, new_password)
    if not success:
        return False, "Could not reset password"
    
    return True, "Password reset successfully" 