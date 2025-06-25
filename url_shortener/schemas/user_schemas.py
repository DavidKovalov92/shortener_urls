from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

class RefreshToken(BaseModel):
    refresh_token: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=100)



class MessageResponse(BaseModel):
    message: str

class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(UserResponse):
    urls_count: int = 0
    total_clicks: int = 0
