# -*- coding: utf-8 -*-
"""
Classes Router
반 관련 API 엔드포인트
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class ClassModel(BaseModel):
    """반 모델"""
    class_id: str
    class_name: str
    teacher_id: str
    schedule: str
    class_start_time: str
    class_end_time: str
    class_cefr: str
    progress: str
    homework: str
    monthly_test: str
    updated_at: str


@router.get("/", response_model=List[ClassModel])
async def get_classes():
    """
    반 목록 조회

    Returns:
        반 목록
    """
    try:
        # Load class.json from data/json/
        class_file = Path("/home/sh/projects/ClassMate/data/json/class.json")

        if not class_file.exists():
            return []

        with open(class_file, "r", encoding="utf-8") as f:
            classes_data = json.load(f)

        return [ClassModel(**cls) for cls in classes_data]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch classes: {str(e)}")


@router.get("/{class_id}", response_model=ClassModel)
async def get_class(class_id: str):
    """
    반 상세 조회

    Args:
        class_id: 반 ID (예: "C-01")

    Returns:
        반 상세 정보
    """
    try:
        class_file = Path("/home/sh/projects/ClassMate/data/json/class.json")

        if not class_file.exists():
            raise HTTPException(status_code=404, detail="Class data not found")

        with open(class_file, "r", encoding="utf-8") as f:
            classes_data = json.load(f)

        # Find class by ID
        for cls in classes_data:
            if cls["class_id"] == class_id:
                return ClassModel(**cls)

        raise HTTPException(status_code=404, detail=f"Class not found: {class_id}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch class: {str(e)}")
