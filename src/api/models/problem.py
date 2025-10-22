# -*- coding: utf-8 -*-
"""
Problem Pydantic Models
문제 관련 데이터 모델
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TableModel(BaseModel):
    """테이블 모델"""
    table_id: str
    problem_id: Optional[str] = None
    title: Optional[str] = None
    columns: List[str] = Field(default_factory=list)
    rows_json: Optional[str] = None
    storage_key: Optional[str] = None
    public_url: Optional[str] = None


class FigureModel(BaseModel):
    """이미지 모델"""
    asset_id: str
    problem_id: Optional[str] = None
    asset_type: Optional[str] = None
    storage_key: Optional[str] = None
    public_url: Optional[str] = None
    mime: Optional[str] = None
    page: Optional[int] = None
    labels: List[str] = Field(default_factory=list)
    caption: Optional[str] = None


class ProblemModel(BaseModel):
    """문제 모델"""
    problem_id: str
    item_no: Optional[int] = None
    area: Optional[str] = None
    mid_code: Optional[str] = None
    grade_band: Optional[str] = None
    cefr: Optional[str] = None
    difficulty: Optional[int] = None
    type: Optional[str] = None
    stem: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    answer: Optional[str] = None
    rationale: Optional[str] = None
    figure_ref: Optional[str] = None
    table_ref: Optional[str] = None
    audio_transcript: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # 관계 데이터
    tables: List[TableModel] = Field(default_factory=list)
    figures: List[FigureModel] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ProblemListResponse(BaseModel):
    """문제 목록 응답"""
    total: int
    skip: int
    limit: int
    problems: List[ProblemModel]


class ProblemSearchRequest(BaseModel):
    """문제 검색 요청"""
    query: str
    limit: int = Field(default=10, ge=1, le=50)


class ProblemSearchResult(BaseModel):
    """문제 검색 결과 (유사도 포함)"""
    problem: ProblemModel
    score: float


class ProblemSearchResponse(BaseModel):
    """문제 검색 응답"""
    query: str
    results: List[ProblemSearchResult]


class ProblemFilterParams(BaseModel):
    """문제 필터 파라미터"""
    area: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    cefr: Optional[str] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
