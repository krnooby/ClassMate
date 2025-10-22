# -*- coding: utf-8 -*-
"""
Auth Router
인증 관련 API 엔드포인트
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class LoginRequest(BaseModel):
    """로그인 요청"""
    student_id: str
    password: str


class LoginResponse(BaseModel):
    """로그인 응답"""
    success: bool
    message: str
    student_id: str | None = None
    parent_id: str | None = None
    teacher_id: str | None = None
    name: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    학생 로그인

    - student_id: students_rag.json에 존재하는 학생 ID (예: S-01, S-02)
    - password: 모든 학생 공통 비밀번호 "test"

    Returns:
        로그인 성공/실패 정보
    """
    # 비밀번호 검증 (모든 학생 공통: "test")
    if request.password != "test":
        return LoginResponse(
            success=False,
            message="비밀번호가 올바르지 않습니다."
        )

    # Neo4j에서 학생 정보 조회
    try:
        from api.services.neo4j_service import Neo4jService

        neo4j_service = Neo4jService.get_instance()

        # Neo4j에서 Student 노드 조회
        query = """
        MATCH (s:Student {student_id: $student_id})
        RETURN s.student_id as student_id, s.name as name
        """

        with neo4j_service.get_session() as session:
            result = session.run(query, student_id=request.student_id)
            record = result.single()

            if not record:
                return LoginResponse(
                    success=False,
                    message="존재하지 않는 학생 ID입니다."
                )

            # 로그인 성공
            return LoginResponse(
                success=True,
                message="로그인 성공",
                student_id=record["student_id"],
                name=record["name"]
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 중 오류: {str(e)}")


@router.post("/logout")
async def logout():
    """
    로그아웃

    (현재는 프론트엔드에서 localStorage만 삭제)
    """
    return {"success": True, "message": "로그아웃 성공"}


@router.post("/parent/login", response_model=LoginResponse)
async def parent_login(request: LoginRequest):
    """
    학부모 로그인

    - student_id: 학부모 ID (예: P-01, P-02)
    - password: 학부모 공통 비밀번호 "parent"

    Returns:
        로그인 성공/실패 정보 (parent_id, 학부모 이름, 자녀 정보 포함)
    """
    # 비밀번호 검증 (모든 학부모 공통: "parent")
    if request.password != "parent":
        return LoginResponse(
            success=False,
            message="비밀번호가 올바르지 않습니다."
        )

    # Neo4j에서 학부모 정보 조회
    try:
        from api.services.neo4j_service import Neo4jService

        neo4j_service = Neo4jService.get_instance()
        parent_id = request.student_id  # 프론트엔드에서 student_id 필드로 전송됨

        # Neo4j에서 Parent 노드와 자녀 정보 조회
        query = """
        MATCH (p:Parent {parent_id: $parent_id})
        OPTIONAL MATCH (p)-[:PARENT_OF]->(s:Student)
        RETURN p.parent_id as parent_id,
               p.name as parent_name,
               s.student_id as student_id,
               s.name as student_name
        """

        with neo4j_service.get_session() as session:
            result = session.run(query, parent_id=parent_id)
            record = result.single()

            if not record or not record["parent_id"]:
                return LoginResponse(
                    success=False,
                    message="존재하지 않는 학부모 ID입니다."
                )

            # 로그인 성공
            parent_name = record["parent_name"]
            student_name = record["student_name"] if record["student_name"] else ""

            display_name = f"{parent_name}"
            if student_name:
                display_name = f"{parent_name} ({student_name} 학부모)"

            return LoginResponse(
                success=True,
                message="로그인 성공",
                parent_id=record["parent_id"],
                student_id=record["student_id"],  # 자녀 ID도 함께 반환
                name=display_name
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 중 오류: {str(e)}")


@router.post("/teacher/login", response_model=LoginResponse)
async def teacher_login(request: LoginRequest):
    """
    선생님 로그인

    - student_id: 선생님 ID (예: T-01, T-02, T-03, T-04)
    - password: 선생님 비밀번호 "teacher"

    Returns:
        로그인 성공/실패 정보
    """
    # 비밀번호 검증 (모든 선생님 공통: "teacher")
    if request.password != "teacher":
        return LoginResponse(
            success=False,
            message="비밀번호가 올바르지 않습니다."
        )

    # Neo4j에서 선생님 정보 조회
    try:
        from api.services.neo4j_service import Neo4jService

        neo4j_service = Neo4jService.get_instance()
        teacher_id = request.student_id  # API receives in student_id field

        # Neo4j에서 Teacher 노드와 담당 반 정보 조회
        query = """
        MATCH (t:Teacher {teacher_id: $teacher_id})
        OPTIONAL MATCH (t)-[:TEACHES]->(c:Class)
        RETURN t.teacher_id as teacher_id,
               t.name as name,
               collect(c.class_name) as class_names
        """

        with neo4j_service.get_session() as session:
            result = session.run(query, teacher_id=teacher_id)
            record = result.single()

            if not record or not record["teacher_id"]:
                return LoginResponse(
                    success=False,
                    message="존재하지 않는 선생님 ID입니다."
                )

            # 반 이름 표시
            class_names = [name for name in record["class_names"] if name]
            class_names_str = ", ".join(class_names) if class_names else ""
            display_name = f"{record['name']}"
            if class_names_str:
                display_name = f"{record['name']} ({class_names_str}반)"

            return LoginResponse(
                success=True,
                message="로그인 성공",
                teacher_id=record["teacher_id"],
                name=display_name
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 중 오류: {str(e)}")
