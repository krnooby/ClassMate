# -*- coding: utf-8 -*-
"""
Students Router
학생 관련 API 엔드포인트
"""
from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException, Query
from api.models.student import (
    StudentModel,
    StudentListResponse,
    StudentSearchRequest,
    StudentSearchResponse,
    StudentSearchResult,
    StudentFilterParams,
    StudentStatsModel
)
from api.services.neo4j_service import Neo4jService


router = APIRouter()


@router.get("/", response_model=StudentListResponse)
async def get_students(
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수"),
    grade_code: str = Query(None, description="학년 코드 필터"),
    cefr: str = Query(None, description="CEFR 레벨 필터")
):
    """
    학생 목록 조회 (필터링 및 페이징)

    - **skip**: 건너뛸 개수 (페이징)
    - **limit**: 가져올 개수 (최대 100)
    - **grade_code**: 학년 코드 필터 (선택)
    - **cefr**: CEFR 레벨 필터 (선택)
    """
    neo4j = Neo4jService.get_instance()

    try:
        students = neo4j.get_students(
            skip=skip,
            limit=limit,
            grade_code=grade_code,
            cefr=cefr
        )

        total = neo4j.count_students(
            grade_code=grade_code,
            cefr=cefr
        )

        return StudentListResponse(
            total=total,
            skip=skip,
            limit=limit,
            students=[StudentModel(**s) for s in students]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch students: {str(e)}")


@router.get("/{student_id}", response_model=StudentModel)
async def get_student(student_id: str):
    """
    학생 상세 조회

    - **student_id**: 학생 ID
    """
    import json
    from pathlib import Path

    students_file = Path("/home/sh/projects/ClassMate/data/json/students_rag.json")

    try:
        with open(students_file, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        # student_id로 학생 찾기 (원본데이터 안에 있음)
        student_raw = None
        for s in students_data:
            original = s.get("원본데이터", {})
            if original.get("student_id") == student_id:
                student_raw = original
                break

        if not student_raw:
            raise HTTPException(status_code=404, detail=f"Student not found: {student_id}")

        # 데이터 구조 변환
        attendance = student_raw.get("attendance", {})
        homework = student_raw.get("homework", {})
        assessment = student_raw.get("assessment", {})
        overall = assessment.get("overall", {})
        radar_scores = assessment.get("radar_scores", {})
        notes = student_raw.get("notes", {})

        # 출석률 계산
        total_sessions = attendance.get("total_sessions", 0)
        absent = attendance.get("absent", 0)
        attendance_rate = (total_sessions - absent) / total_sessions if total_sessions > 0 else 0

        # 숙제 완료율 계산
        assigned = homework.get("assigned", 0)
        missed = homework.get("missed", 0)
        homework_completion_rate = (assigned - missed) / assigned if assigned > 0 else 0

        student = {
            "student_id": student_raw.get("student_id"),
            "name": student_raw.get("name"),
            "class_id": student_raw.get("class_id"),
            "grade_code": student_raw.get("grade_code"),
            "grade_label": student_raw.get("grade_label"),
            "attendance_rate": attendance_rate,
            "total_sessions": total_sessions,
            "absent": absent,
            "homework_completion_rate": homework_completion_rate,
            "homework_assigned": assigned,
            "homework_missed": missed,
            "grammar_score": radar_scores.get("grammar"),
            "vocabulary_score": radar_scores.get("vocabulary"),
            "reading_score": radar_scores.get("reading"),
            "listening_score": radar_scores.get("listening"),
            "writing_score": radar_scores.get("writing"),
            "cefr": overall.get("cefr"),
            "percentile_rank": overall.get("percentile_rank"),
            "attitude": notes.get("attitude"),
            "school_exam_level": notes.get("school_exam_level"),
            "csat_level": notes.get("csat_level"),
            "summary": None  # 요약은 별도로 처리
        }

        return StudentModel(**student)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch student: {str(e)}")


@router.get("/{student_id}/stats", response_model=StudentStatsModel)
async def get_student_stats(student_id: str):
    """
    학생 통계 조회

    - **student_id**: 학생 ID
    """
    import json
    from pathlib import Path

    students_file = Path("/home/sh/projects/ClassMate/data/json/students_rag.json")

    try:
        with open(students_file, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        # student_id로 학생 찾기 (원본데이터 안에 있음)
        student_raw = None
        for s in students_data:
            original = s.get("원본데이터", {})
            if original.get("student_id") == student_id:
                student_raw = original
                break

        if not student_raw:
            raise HTTPException(status_code=404, detail=f"Student not found: {student_id}")

        # 데이터 구조 변환
        attendance = student_raw.get("attendance", {})
        homework = student_raw.get("homework", {})
        assessment = student_raw.get("assessment", {})
        overall = assessment.get("overall", {})
        radar_scores = assessment.get("radar_scores", {})

        # 출석률 계산
        total_sessions = attendance.get("total_sessions", 0)
        absent = attendance.get("absent", 0)
        attendance_rate = (total_sessions - absent) / total_sessions if total_sessions > 0 else 0

        # 숙제 완료율 계산
        assigned = homework.get("assigned", 0)
        missed = homework.get("missed", 0)
        homework_completion_rate = (assigned - missed) / assigned if assigned > 0 else 0

        # 평균 점수 계산
        scores = [
            radar_scores.get("grammar"),
            radar_scores.get("vocabulary"),
            radar_scores.get("reading"),
            radar_scores.get("listening"),
            radar_scores.get("writing")
        ]
        valid_scores = [s for s in scores if s is not None]
        average_score = sum(valid_scores) / len(valid_scores) if valid_scores else None

        return StudentStatsModel(
            student_id=student_raw.get("student_id"),
            name=student_raw.get("name"),
            attendance_rate=attendance_rate,
            total_sessions=total_sessions,
            absent=absent,
            homework_completion_rate=homework_completion_rate,
            homework_assigned=assigned,
            homework_missed=missed,
            average_score=average_score,
            grammar_score=radar_scores.get("grammar"),
            vocabulary_score=radar_scores.get("vocabulary"),
            reading_score=radar_scores.get("reading"),
            listening_score=radar_scores.get("listening"),
            writing_score=radar_scores.get("writing"),
            cefr=overall.get("cefr"),
            percentile_rank=overall.get("percentile_rank")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch student stats: {str(e)}")


@router.post("/search", response_model=StudentSearchResponse)
async def search_students(request: StudentSearchRequest):
    """
    학생 검색 (임베딩 기반 유사도 검색)

    - **query**: 검색 쿼리 텍스트
    - **limit**: 결과 개수 (1-50)
    """
    neo4j = Neo4jService.get_instance()

    try:
        results = neo4j.search_students_by_text(
            query_text=request.query,
            limit=request.limit
        )

        return StudentSearchResponse(
            query=request.query,
            results=[
                StudentSearchResult(
                    student=StudentModel(**student),
                    score=score
                )
                for student, score in results
            ]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
