# -*- coding: utf-8 -*-
"""
Problems Router
문제 관련 API 엔드포인트
"""
from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException, Query
from api.models.problem import (
    ProblemModel,
    ProblemListResponse,
    ProblemSearchRequest,
    ProblemSearchResponse,
    ProblemSearchResult,
    ProblemFilterParams,
    TableModel,
    FigureModel
)
from api.services.neo4j_service import Neo4jService


router = APIRouter()


@router.get("/", response_model=ProblemListResponse)
async def get_problems(
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수"),
    area: str = Query(None, description="영역 필터 (LS, RC 등)"),
    difficulty: int = Query(None, ge=1, le=5, description="난이도 필터 (1-5)"),
    cefr: str = Query(None, description="CEFR 레벨 필터")
):
    """
    문제 목록 조회 (필터링 및 페이징)

    - **skip**: 건너뛸 개수 (페이징)
    - **limit**: 가져올 개수 (최대 100)
    - **area**: 영역 필터 (LS, RC 등) - 선택
    - **difficulty**: 난이도 필터 (1-5) - 선택
    - **cefr**: CEFR 레벨 필터 - 선택
    """
    neo4j = Neo4jService.get_instance()

    try:
        problems = neo4j.get_problems(
            skip=skip,
            limit=limit,
            area=area,
            difficulty=difficulty,
            cefr=cefr
        )

        total = neo4j.count_problems(
            area=area,
            difficulty=difficulty,
            cefr=cefr
        )

        # Convert to Pydantic models
        problem_models = []
        for p in problems:
            # Convert tables and figures
            tables = [TableModel(**t) for t in p.get("tables", [])]
            figures = [FigureModel(**f) for f in p.get("figures", [])]

            # Remove nested data and add them separately
            p_copy = p.copy()
            p_copy.pop("tables", None)
            p_copy.pop("figures", None)

            problem_model = ProblemModel(**p_copy)
            problem_model.tables = tables
            problem_model.figures = figures

            problem_models.append(problem_model)

        return ProblemListResponse(
            total=total,
            skip=skip,
            limit=limit,
            problems=problem_models
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch problems: {str(e)}")


@router.get("/{problem_id}", response_model=ProblemModel)
async def get_problem(problem_id: str):
    """
    문제 상세 조회

    - **problem_id**: 문제 ID (예: "2026_09_mock-0001")
    """
    neo4j = Neo4jService.get_instance()

    try:
        problem = neo4j.get_problem_by_id(problem_id)

        if not problem:
            raise HTTPException(status_code=404, detail=f"Problem not found: {problem_id}")

        # Convert tables and figures
        tables = [TableModel(**t) for t in problem.get("tables", [])]
        figures = [FigureModel(**f) for f in problem.get("figures", [])]

        # Remove nested data and add them separately
        problem.pop("tables", None)
        problem.pop("figures", None)

        problem_model = ProblemModel(**problem)
        problem_model.tables = tables
        problem_model.figures = figures

        return problem_model

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch problem: {str(e)}")


@router.post("/search", response_model=ProblemSearchResponse)
async def search_problems(request: ProblemSearchRequest):
    """
    문제 검색 (임베딩 기반 유사도 검색)

    - **query**: 검색 쿼리 텍스트
    - **limit**: 결과 개수 (1-50)
    """
    neo4j = Neo4jService.get_instance()

    try:
        results = neo4j.search_problems_by_text(
            query_text=request.query,
            limit=request.limit
        )

        search_results = []
        for problem, score in results:
            # Convert tables and figures
            tables = [TableModel(**t) for t in problem.get("tables", [])]
            figures = [FigureModel(**f) for f in problem.get("figures", [])]

            # Remove nested data
            problem.pop("tables", None)
            problem.pop("figures", None)

            problem_model = ProblemModel(**problem)
            problem_model.tables = tables
            problem_model.figures = figures

            search_results.append(
                ProblemSearchResult(
                    problem=problem_model,
                    score=score
                )
            )

        return ProblemSearchResponse(
            query=request.query,
            results=search_results
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
