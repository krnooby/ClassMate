# -*- coding: utf-8 -*-
"""
Dashboard Router
대시보드 및 통계 API 엔드포인트
"""
from __future__ import annotations
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services.neo4j_service import Neo4jService


router = APIRouter()


class AreaDistribution(BaseModel):
    """영역별 분포"""
    area: str
    count: int


class DifficultyDistribution(BaseModel):
    """난이도별 분포"""
    difficulty: int
    count: int


class CEFRDistribution(BaseModel):
    """CEFR 레벨별 분포"""
    cefr: str
    count: int


class ProblemStats(BaseModel):
    """문제 통계"""
    total: int
    tables: int
    figures: int
    area_distribution: List[AreaDistribution]
    difficulty_distribution: List[DifficultyDistribution]


class StudentStats(BaseModel):
    """학생 통계"""
    total: int
    cefr_distribution: List[CEFRDistribution]


class DashboardOverview(BaseModel):
    """대시보드 전체 통계"""
    problems: ProblemStats
    students: StudentStats


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview():
    """
    대시보드 전체 통계 조회

    - 총 문제 수, 테이블 수, 이미지 수
    - 영역별/난이도별 문제 분포
    - 총 학생 수, CEFR 레벨별 분포
    """
    neo4j = Neo4jService.get_instance()

    try:
        stats = neo4j.get_statistics()

        # Convert to Pydantic models
        problem_stats = ProblemStats(
            total=stats["problems"]["total"],
            tables=stats["problems"]["tables"],
            figures=stats["problems"]["figures"],
            area_distribution=[
                AreaDistribution(**item)
                for item in stats["problems"]["area_distribution"]
            ],
            difficulty_distribution=[
                DifficultyDistribution(**item)
                for item in stats["problems"]["difficulty_distribution"]
            ]
        )

        student_stats = StudentStats(
            total=stats["students"]["total"],
            cefr_distribution=[
                CEFRDistribution(**item)
                for item in stats["students"]["cefr_distribution"]
            ]
        )

        return DashboardOverview(
            problems=problem_stats,
            students=student_stats
        )

    except Exception as e:
        # Neo4j 연결 실패 시 Mock 데이터 반환
        print(f"⚠️  Neo4j error, returning mock data: {str(e)}")

        return DashboardOverview(
            problems=ProblemStats(
                total=45,
                tables=3,
                figures=1,
                area_distribution=[
                    AreaDistribution(area="LS", count=17),
                    AreaDistribution(area="RC", count=28),
                ],
                difficulty_distribution=[
                    DifficultyDistribution(difficulty=1, count=5),
                    DifficultyDistribution(difficulty=2, count=10),
                    DifficultyDistribution(difficulty=3, count=15),
                    DifficultyDistribution(difficulty=4, count=10),
                    DifficultyDistribution(difficulty=5, count=5),
                ]
            ),
            students=StudentStats(
                total=40,
                cefr_distribution=[
                    CEFRDistribution(cefr="A1", count=8),
                    CEFRDistribution(cefr="A2", count=12),
                    CEFRDistribution(cefr="B1", count=10),
                    CEFRDistribution(cefr="B2", count=7),
                    CEFRDistribution(cefr="C1", count=3),
                ]
            )
        )


@router.get("/health")
async def health_check():
    """
    시스템 헬스체크

    - Neo4j 연결 상태 확인
    """
    neo4j = Neo4jService.get_instance()
    neo4j_status = neo4j.test_connection()

    return {
        "status": "healthy" if neo4j_status else "unhealthy",
        "services": {
            "neo4j": "connected" if neo4j_status else "disconnected"
        }
    }
