# -*- coding: utf-8 -*-
"""
Chat Router (통합)
도메인별 라우터를 통합
"""
from fastapi import APIRouter
from student.routers.chat import router as student_router
from parent.routers.chat import router as parent_router
from teacher.routers.chat import router as teacher_router

# 메인 라우터 생성
router = APIRouter()

# 도메인별 라우터 포함
router.include_router(student_router, tags=["Student Chat"])
router.include_router(parent_router, tags=["Parent Chat"])
router.include_router(teacher_router, tags=["Teacher Chat"])
