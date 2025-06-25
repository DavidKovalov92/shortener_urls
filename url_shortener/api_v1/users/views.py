from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from .email_service import send_email


from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from jwt.jwt_handler import create_url_safe_token, decode_url_safe_token, get_password_hash
from .dependencies import get_current_user, get_db
from .crud import (
    update_user_profile, delete_user, register_user_with_validation,
    login_user_with_validation, change_user_password_with_validation,
    initiate_password_reset, complete_password_reset, get_user_by_email, update_user
)
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

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    email_data: PasswordReset,
    background_tasks: BackgroundTasks,
):
    email = email_data.email

    token = create_url_safe_token({"email": email})

    link = f"http://localhost:8000/api/v1/users/reset-password-confirm/{token}"

    html = f"""
    <h1>Reset your Password</h1>
    <p>Please click this <a href="{link}">link</a> to Reset your Password</p>
    """

    emails = [email]

    subject = "Verify Your email"

    background_tasks.add_task(send_email, emails, subject, html)


    return JSONResponse(
        content={
            "message": "Check email to reset your password",
        },
        status_code=status.HTTP_200_OK
    )

@router.post("/reset-password-confirm/{token}")
async def reset_account_password(
    token: str,
    passwords: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    new_password = passwords.new_password
    confirm_password = passwords.confirm_new_password

    if new_password != confirm_password:
        raise HTTPException(
            detail="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        token_data = decode_url_safe_token(token)
        user_email = token_data.get("email")

        if user_email:
            user = await get_user_by_email(db, user_email)

            if not user:
                raise HTTPException(
                    detail="User not found", status_code=status.HTTP_404_NOT_FOUND
                )

            passwd_hash = get_password_hash(new_password)
            await update_user(db, user, {"password": passwd_hash})

            return JSONResponse(
                content={"message": "Password reset successfully"},
                status_code=status.HTTP_200_OK,
            )
    except Exception as e:
        print(f"Error in password reset: {e}")
        raise HTTPException(
            detail="Invalid or expired token", 
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return JSONResponse(
        content={"message": "Error occurred during password reset."},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

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