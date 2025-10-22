# -*- coding: utf-8 -*-
"""
Student Pydantic Models
학생 관련 데이터 모델
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StudentModel(BaseModel):
    """학생 모델"""
    student_id: str
    name: str
    class_id: Optional[str] = None
    grade_code: Optional[str] = None
    grade_label: Optional[str] = None
    updated_at: Optional[str] = None
    summary: Optional[str] = None

    # 출석 정보
    total_sessions: Optional[int] = None
    absent: Optional[int] = None
    perception: Optional[str] = None
    attendance_rate: Optional[float] = None

    # 숙제 정보
    homework_assigned: Optional[int] = None
    homework_missed: Optional[int] = None
    homework_completion_rate: Optional[float] = None

    # 평가 정보
    attitude: Optional[str] = None
    school_exam_level: Optional[str] = None
    csat_level: Optional[str] = None
    cefr: Optional[str] = None
    percentile_rank: Optional[int] = None

    # 점수 정보
    grammar_score: Optional[float] = None
    vocabulary_score: Optional[float] = None
    reading_score: Optional[float] = None
    listening_score: Optional[float] = None
    writing_score: Optional[float] = None

    # 동료 분포 (JSON 문자열 또는 dict)
    peer_distribution: Optional[str] = None

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    """학생 목록 응답"""
    total: int
    skip: int
    limit: int
    students: List[StudentModel]


class StudentSearchRequest(BaseModel):
    """학생 검색 요청"""
    query: str
    limit: int = Field(default=10, ge=1, le=50)


class StudentSearchResult(BaseModel):
    """학생 검색 결과 (유사도 포함)"""
    student: StudentModel
    score: float


class StudentSearchResponse(BaseModel):
    """학생 검색 응답"""
    query: str
    results: List[StudentSearchResult]


class StudentFilterParams(BaseModel):
    """학생 필터 파라미터"""
    grade_code: Optional[str] = None
    cefr: Optional[str] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class StudentStatsModel(BaseModel):
    """학생 통계 모델"""
    student_id: str
    name: str

    # 출석
    attendance_rate: Optional[float] = None
    total_sessions: Optional[int] = None
    absent: Optional[int] = None

    # 숙제
    homework_completion_rate: Optional[float] = None
    homework_assigned: Optional[int] = None
    homework_missed: Optional[int] = None

    # 점수
    average_score: Optional[float] = None
    grammar_score: Optional[float] = None
    vocabulary_score: Optional[float] = None
    reading_score: Optional[float] = None
    listening_score: Optional[float] = None
    writing_score: Optional[float] = None

    # 레벨
    cefr: Optional[str] = None
    percentile_rank: Optional[int] = None
