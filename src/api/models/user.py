# -*- coding: utf-8 -*-
"""
User Pydantic Models
사용자 인증 관련 데이터 모델
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class UserRole(str, Enum):
    """사용자 역할"""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class UserModel(BaseModel):
    """사용자 모델"""
    user_id: str
    username: str
    email: Optional[EmailStr] = None
    role: UserRole
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    """사용자 생성 요청"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.STUDENT


class UserLoginRequest(BaseModel):
    """로그인 요청"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """토큰 응답"""
    access_token: str
    token_type: str = "bearer"
    user: UserModel


class UserUpdateRequest(BaseModel):
    """사용자 정보 수정 요청"""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
