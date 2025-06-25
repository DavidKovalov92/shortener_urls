from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from .dependencies import get_current_user, get_db
from .crud import (
    update_user_profile, delete_user, register_user_with_validation,
    login_user_with_validation, change_user_password_with_validation,
    initiate_password_reset, complete_password_reset
)
from .email_service import send_password_reset_email, send_welcome_email
from schemas.user_schemas import (
    UserCreate, UserLogin, UserResponse, UserLoginResponse, 
    PasswordChange, MessageResponse, PasswordReset, PasswordResetConfirm,
    UserProfile
)
from jwt.jwt_handler import (
    create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, 
    verify_password, create_reset_token, verify_reset_token
)
from models.user_model import User

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    user, message = await register_user_with_validation(db, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    background_tasks.add_task(send_welcome_email, user.email, user.username)
    
    return user

@router.post("/login", response_model=UserLoginResponse)
async def login(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    user, message = await login_user_with_validation(
        db, user_credentials.email, user_credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "username": user.username},
        expires_delta=access_token_expires
    )
    
    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    updated_user = await update_user_profile(db, current_user.id, username)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken or invalid"
        )
    return updated_user

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    success, message = await change_user_password_with_validation(
        db, 
        current_user.id, 
        password_data.current_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return MessageResponse(message=message)

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    password_reset: PasswordReset,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    success, message, reset_token = await initiate_password_reset(db, password_reset.email)
    
    if reset_token:
        background_tasks.add_task(send_password_reset_email, password_reset.email, reset_token)
    
    return MessageResponse(message=message)

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    success, message = await complete_password_reset(db, reset_data.token, reset_data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return MessageResponse(message=message)

@router.delete("/delete-account", response_model=MessageResponse)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    success = await delete_user(db, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete account"
        )
    
    return MessageResponse(message="Account deleted successfully")

@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    return MessageResponse(message="Successfully logged out") 