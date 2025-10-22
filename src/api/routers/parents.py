# -*- coding: utf-8 -*-
"""
Parents Router
학부모 관련 API 엔드포인트
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from api.services.neo4j_service import Neo4jService


router = APIRouter()


class ParentInfo(BaseModel):
    """학부모 정보"""
    parent_id: str
    name: str
    contact: Optional[str] = None
    children: List[Dict[str, Any]] = []


class ChildSummary(BaseModel):
    """자녀 요약 정보"""
    student_id: str
    name: str
    class_id: str
    cefr_level: Optional[str] = None
    attendance_rate: Optional[float] = None
    homework_rate: Optional[float] = None


class ParentDashboard(BaseModel):
    """학부모 대시보드"""
    parent_id: str
    parent_name: str
    children: List[ChildSummary]
    total_children: int


@router.get("/", response_model=List[ParentInfo])
async def get_all_parents(
    limit: int = Query(default=50, ge=1, le=100, description="조회할 학부모 수")
):
    """
    전체 학부모 목록 조회

    - **limit**: 조회할 학부모 수 (기본값: 50, 최대: 100)

    Returns:
        학부모 목록
    """
    try:
        neo4j_service = Neo4jService.get_instance()

        # Neo4j에서 학부모 목록 조회
        query = """
        MATCH (p:Parent)
        OPTIONAL MATCH (p)-[:PARENT_OF]->(s:Student)
        WITH p, collect({
            student_id: s.student_id,
            name: s.name,
            class_id: s.class_id
        }) as children
        RETURN p.parent_id as parent_id,
               p.name as name,
               p.contact as contact,
               children
        LIMIT $limit
        """

        with neo4j_service.get_session() as session:
            result = session.run(query, limit=limit)

            parents = []
            for record in result:
                parents.append(ParentInfo(
                    parent_id=record["parent_id"],
                    name=record["name"],
                    contact=record.get("contact"),
                    children=[child for child in record["children"] if child["student_id"]]
                ))

            return parents

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch parents: {str(e)}")


@router.get("/{parent_id}", response_model=ParentInfo)
async def get_parent(parent_id: str):
    """
    학부모 상세 정보 조회

    - **parent_id**: 학부모 ID (예: P-01)

    Returns:
        학부모 상세 정보 및 자녀 목록
    """
    try:
        neo4j_service = Neo4jService.get_instance()

        # Neo4j에서 학부모 정보 조회
        query = """
        MATCH (p:Parent {parent_id: $parent_id})
        OPTIONAL MATCH (p)-[:PARENT_OF]->(s:Student)
        WITH p, collect({
            student_id: s.student_id,
            name: s.name,
            class_id: s.class_id
        }) as children
        RETURN p.parent_id as parent_id,
               p.name as name,
               p.contact as contact,
               children
        """

        with neo4j_service.get_session() as session:
            result = session.run(query, parent_id=parent_id)
            record = result.single()

            if not record:
                raise HTTPException(status_code=404, detail=f"Parent {parent_id} not found")

            return ParentInfo(
                parent_id=record["parent_id"],
                name=record["name"],
                contact=record.get("contact"),
                children=[child for child in record["children"] if child["student_id"]]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch parent: {str(e)}")


@router.get("/{parent_id}/dashboard", response_model=ParentDashboard)
async def get_parent_dashboard(parent_id: str):
    """
    학부모 대시보드 (자녀 학습 현황 요약)

    - **parent_id**: 학부모 ID

    Returns:
        자녀들의 학습 현황 요약
    """
    try:
        neo4j_service = Neo4jService.get_instance()

        # Neo4j에서 학부모와 자녀들의 학습 현황 조회
        query = """
        MATCH (p:Parent {parent_id: $parent_id})
        OPTIONAL MATCH (p)-[:PARENT_OF]->(s:Student)
        OPTIONAL MATCH (s)-[:HAS_ASSESSMENT]->(a:Assessment)
        OPTIONAL MATCH (s)-[:HAS_ATTENDANCE]->(att:Attendance)
        OPTIONAL MATCH (s)-[:HAS_HOMEWORK]->(hw:Homework)
        WITH p, s, a, att, hw
        RETURN p.parent_id as parent_id,
               p.name as parent_name,
               collect({
                   student_id: s.student_id,
                   name: s.name,
                   class_id: s.class_id,
                   cefr_level: a.cefr_level,
                   attendance_rate: CASE
                       WHEN att.total_sessions > 0
                       THEN toFloat(att.total_sessions - att.absent) / att.total_sessions * 100
                       ELSE null
                   END,
                   homework_rate: CASE
                       WHEN hw.assigned > 0
                       THEN toFloat(hw.assigned - hw.missed) / hw.assigned * 100
                       ELSE null
                   END
               }) as children
        """

        with neo4j_service.get_session() as session:
            result = session.run(query, parent_id=parent_id)
            record = result.single()

            if not record:
                raise HTTPException(status_code=404, detail=f"Parent {parent_id} not found")

            # Filter out null children (when no PARENT_OF relationship exists)
            children_data = [
                ChildSummary(
                    student_id=child["student_id"],
                    name=child["name"],
                    class_id=child["class_id"],
                    cefr_level=child.get("cefr_level"),
                    attendance_rate=child.get("attendance_rate"),
                    homework_rate=child.get("homework_rate")
                )
                for child in record["children"]
                if child["student_id"]
            ]

            return ParentDashboard(
                parent_id=record["parent_id"],
                parent_name=record["parent_name"],
                children=children_data,
                total_children=len(children_data)
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard: {str(e)}")


@router.get("/student/{student_id}/parent", response_model=ParentInfo)
async def get_parent_by_student(student_id: str):
    """
    학생 ID로 학부모 정보 조회

    - **student_id**: 학생 ID (예: S-01)

    Returns:
        해당 학생의 학부모 정보
    """
    try:
        neo4j_service = Neo4jService.get_instance()

        # Neo4j에서 학생의 학부모 조회
        query = """
        MATCH (p:Parent)-[:PARENT_OF]->(s:Student {student_id: $student_id})
        OPTIONAL MATCH (p)-[:PARENT_OF]->(all_children:Student)
        WITH p, collect({
            student_id: all_children.student_id,
            name: all_children.name,
            class_id: all_children.class_id
        }) as children
        RETURN p.parent_id as parent_id,
               p.name as name,
               p.contact as contact,
               children
        """

        with neo4j_service.get_session() as session:
            result = session.run(query, student_id=student_id)
            record = result.single()

            if not record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Parent not found for student {student_id}"
                )

            return ParentInfo(
                parent_id=record["parent_id"],
                name=record["name"],
                contact=record.get("contact"),
                children=[child for child in record["children"] if child["student_id"]]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch parent: {str(e)}")
