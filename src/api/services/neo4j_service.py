# -*- coding: utf-8 -*-
"""
Neo4j Service Layer
Singleton pattern for managing Neo4j connections and queries
"""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional, Tuple
from neo4j import GraphDatabase, Driver, Session


class Neo4jService:
    """Neo4j 데이터베이스 서비스 (Singleton)"""

    _instance: Optional[Neo4jService] = None
    _initialized: bool = False

    def __init__(self):
        """직접 호출하지 말고 get_instance() 사용"""
        pass

    def _initialize(self):
        """실제 초기화 (한 번만 실행)"""
        if self._initialized:
            return

        self.uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        # NEO4J_USER 또는 NEO4J_USERNAME 둘 다 지원
        self.username = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.database = os.getenv("NEO4J_DATABASE") or os.getenv("NEO4J_DB", "classmate")

        self._driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
            connection_timeout=3.0,  # 3초 타임아웃
            max_connection_lifetime=3600
        )
        self._initialized = True

    @classmethod
    def get_instance(cls) -> Neo4jService:
        """Singleton 인스턴스 가져오기"""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def get_session(self) -> Session:
        """Neo4j 세션 가져오기"""
        if not self._initialized or self._driver is None:
            raise RuntimeError("Driver not initialized")
        return self._driver.session(database=self.database)

    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            with self.get_session() as session:
                result = session.run("RETURN 1 as num")
                return result.single()["num"] == 1
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
            return False

    def close(self):
        """연결 종료"""
        if self._driver:
            self._driver.close()
            self._driver = None

    # ==================== Problem 관련 메서드 ====================

    def get_problems(
        self,
        skip: int = 0,
        limit: int = 20,
        area: Optional[str] = None,
        difficulty: Optional[int] = None,
        cefr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        문제 목록 조회 (필터링 및 페이징)

        Args:
            skip: 건너뛸 개수
            limit: 가져올 개수
            area: 영역 필터 (LS, RC 등)
            difficulty: 난이도 필터 (1-5)
            cefr: CEFR 레벨 필터 (A1, A2, B1, B2, C1, C2)

        Returns:
            문제 목록
        """
        where_clauses = []
        params = {"skip": skip, "limit": limit}

        if area:
            where_clauses.append("p.area = $area")
            params["area"] = area

        if difficulty:
            where_clauses.append("p.difficulty = $difficulty")
            params["difficulty"] = difficulty

        if cefr:
            where_clauses.append("p.cefr = $cefr")
            params["cefr"] = cefr

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            MATCH (p:Problem)
            WHERE {where_clause}
            OPTIONAL MATCH (p)-[:HAS_TABLE]->(t:Tbl)
            OPTIONAL MATCH (p)-[:HAS_FIG]->(f:Fig)
            RETURN p, collect(DISTINCT t) as tables, collect(DISTINCT f) as figures
            ORDER BY p.item_no
            SKIP $skip
            LIMIT $limit
        """

        with self.get_session() as session:
            results = session.run(query, **params)
            problems = []

            for record in results:
                problem_node = record["p"]
                problem = dict(problem_node)

                # 테이블/이미지 정보 추가
                problem["tables"] = [dict(t) for t in record["tables"] if t is not None]
                problem["figures"] = [dict(f) for f in record["figures"] if f is not None]

                # 임베딩은 제거 (너무 큼)
                problem.pop("search_embedding", None)
                problem.pop("stem_embedding", None)
                problem.pop("rationale_embedding", None)

                problems.append(problem)

            return problems

    def get_problem_by_id(self, problem_id: str) -> Optional[Dict[str, Any]]:
        """
        문제 상세 조회

        Args:
            problem_id: 문제 ID (예: "2026_09_mock-0001")

        Returns:
            문제 상세 정보 또는 None
        """
        query = """
            MATCH (p:Problem {problem_id: $problem_id})
            OPTIONAL MATCH (p)-[:HAS_TABLE]->(t:Tbl)
            OPTIONAL MATCH (p)-[:HAS_FIG]->(f:Fig)
            RETURN p, collect(DISTINCT t) as tables, collect(DISTINCT f) as figures
        """

        with self.get_session() as session:
            result = session.run(query, problem_id=problem_id)
            record = result.single()

            if not record:
                return None

            problem_node = record["p"]
            problem = dict(problem_node)

            # 테이블/이미지 정보 추가
            problem["tables"] = [dict(t) for t in record["tables"] if t is not None]
            problem["figures"] = [dict(f) for f in record["figures"] if f is not None]

            # 임베딩은 제거 (너무 큼)
            problem.pop("search_embedding", None)
            problem.pop("stem_embedding", None)
            problem.pop("rationale_embedding", None)

            return problem

    def count_problems(
        self,
        area: Optional[str] = None,
        difficulty: Optional[int] = None,
        cefr: Optional[str] = None
    ) -> int:
        """문제 총 개수 (필터링 적용)"""
        where_clauses = []
        params = {}

        if area:
            where_clauses.append("p.area = $area")
            params["area"] = area

        if difficulty:
            where_clauses.append("p.difficulty = $difficulty")
            params["difficulty"] = difficulty

        if cefr:
            where_clauses.append("p.cefr = $cefr")
            params["cefr"] = cefr

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            MATCH (p:Problem)
            WHERE {where_clause}
            RETURN count(p) as total
        """

        with self.get_session() as session:
            result = session.run(query, **params)
            return result.single()["total"]

    # ==================== Student 관련 메서드 ====================

    def get_students(
        self,
        skip: int = 0,
        limit: int = 20,
        grade_code: Optional[str] = None,
        cefr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        학생 목록 조회 (필터링 및 페이징)

        Args:
            skip: 건너뛸 개수
            limit: 가져올 개수
            grade_code: 학년 코드 필터
            cefr: CEFR 레벨 필터

        Returns:
            학생 목록
        """
        where_clauses = []
        params = {"skip": skip, "limit": limit}

        if grade_code:
            where_clauses.append("s.grade_code = $grade_code")
            params["grade_code"] = grade_code

        if cefr:
            where_clauses.append("s.cefr = $cefr")
            params["cefr"] = cefr

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            MATCH (s:Student)
            WHERE {where_clause}
            RETURN s
            ORDER BY s.student_id
            SKIP $skip
            LIMIT $limit
        """

        with self.get_session() as session:
            results = session.run(query, **params)
            students = []

            for record in results:
                student_node = record["s"]
                student = dict(student_node)

                # 임베딩 제거
                student.pop("student_embedding", None)

                students.append(student)

            return students

    def get_student_by_id(self, student_id: str) -> Optional[Dict[str, Any]]:
        """
        학생 상세 조회

        Args:
            student_id: 학생 ID

        Returns:
            학생 상세 정보 또는 None
        """
        query = """
            MATCH (s:Student {student_id: $student_id})
            RETURN s
        """

        with self.get_session() as session:
            result = session.run(query, student_id=student_id)
            record = result.single()

            if not record:
                return None

            student_node = record["s"]
            student = dict(student_node)

            # 임베딩 제거
            student.pop("student_embedding", None)

            return student

    def count_students(
        self,
        grade_code: Optional[str] = None,
        cefr: Optional[str] = None
    ) -> int:
        """학생 총 개수 (필터링 적용)"""
        where_clauses = []
        params = {}

        if grade_code:
            where_clauses.append("s.grade_code = $grade_code")
            params["grade_code"] = grade_code

        if cefr:
            where_clauses.append("s.cefr = $cefr")
            params["cefr"] = cefr

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            MATCH (s:Student)
            WHERE {where_clause}
            RETURN count(s) as total
        """

        with self.get_session() as session:
            result = session.run(query, **params)
            return result.single()["total"]

    # ==================== 통계 메서드 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """전체 통계 조회"""
        with self.get_session() as session:
            # 문제 통계
            problem_count = session.run("MATCH (p:Problem) RETURN count(p) as cnt").single()["cnt"]
            table_count = session.run("MATCH (t:Tbl) RETURN count(t) as cnt").single()["cnt"]
            figure_count = session.run("MATCH (f:Fig) RETURN count(f) as cnt").single()["cnt"]

            # 학생 통계
            student_count = session.run("MATCH (s:Student) RETURN count(s) as cnt").single()["cnt"]

            # 문제 영역별 분포
            area_dist = session.run("""
                MATCH (p:Problem)
                RETURN p.area as area, count(p) as count
                ORDER BY area
            """)
            area_distribution = [dict(record) for record in area_dist]

            # 난이도별 분포
            diff_dist = session.run("""
                MATCH (p:Problem)
                WHERE p.difficulty IS NOT NULL
                RETURN p.difficulty as difficulty, count(p) as count
                ORDER BY difficulty
            """)
            difficulty_distribution = [dict(record) for record in diff_dist]

            # 학생 CEFR 분포
            cefr_dist = session.run("""
                MATCH (s:Student)
                WHERE s.cefr IS NOT NULL
                RETURN s.cefr as cefr, count(s) as count
                ORDER BY cefr
            """)
            cefr_distribution = [dict(record) for record in cefr_dist]

            return {
                "problems": {
                    "total": problem_count,
                    "tables": table_count,
                    "figures": figure_count,
                    "area_distribution": area_distribution,
                    "difficulty_distribution": difficulty_distribution
                },
                "students": {
                    "total": student_count,
                    "cefr_distribution": cefr_distribution
                }
            }

    # ==================== 검색 메서드 ====================

    def search_problems_by_text(
        self,
        query_text: str,
        limit: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        텍스트 기반 문제 검색 (임베딩 유사도)

        Args:
            query_text: 검색 텍스트
            limit: 결과 개수

        Returns:
            (문제, 유사도 점수) 튜플 리스트
        """
        # 임베딩 생성 (여기서는 teacher.shared.embeddings 사용)
        from teacher.shared.embeddings import embed_text

        query_embedding = embed_text(query_text)

        query = """
            CALL db.index.vector.queryNodes('problem_search_index', $limit, $query_embedding)
            YIELD node, score
            RETURN node, score
            ORDER BY score DESC
        """

        with self.get_session() as session:
            results = session.run(query, limit=limit, query_embedding=query_embedding)
            search_results = []

            for record in results:
                problem_node = record["node"]
                score = record["score"]

                problem = dict(problem_node)

                # 임베딩 제거
                problem.pop("search_embedding", None)
                problem.pop("stem_embedding", None)
                problem.pop("rationale_embedding", None)

                search_results.append((problem, score))

            return search_results

    def search_students_by_text(
        self,
        query_text: str,
        limit: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        텍스트 기반 학생 검색 (임베딩 유사도)

        Args:
            query_text: 검색 텍스트
            limit: 결과 개수

        Returns:
            (학생, 유사도 점수) 튜플 리스트
        """
        # 임베딩 생성
        from teacher.shared.embeddings import embed_text

        query_embedding = embed_text(query_text)

        query = """
            CALL db.index.vector.queryNodes('student_search_index', $limit, $query_embedding)
            YIELD node, score
            RETURN node, score
            ORDER BY score DESC
        """

        with self.get_session() as session:
            results = session.run(query, limit=limit, query_embedding=query_embedding)
            search_results = []

            for record in results:
                student_node = record["node"]
                score = record["score"]

                student = dict(student_node)

                # 임베딩 제거
                student.pop("student_embedding", None)

                search_results.append((student, score))

            return search_results

    # ==================== Daily Input 메서드 ====================

    def create_daily_input(
        self,
        input_id: str,
        student_id: str,
        date: str,
        content: str,
        category: str,
        teacher_id: str
    ) -> bool:
        """
        Daily Input 생성

        Args:
            input_id: Input ID
            student_id: 학생 ID
            date: 날짜 (YYYY-MM-DD)
            content: 내용
            category: 카테고리
            teacher_id: 선생님 ID

        Returns:
            성공 여부
        """
        from datetime import datetime

        query = """
            MATCH (s:Student {student_id: $student_id})
            CREATE (i:DailyInput {
                input_id: $input_id,
                date: $date,
                content: $content,
                category: $category,
                teacher_id: $teacher_id,
                created_at: $created_at
            })
            CREATE (s)-[:HAS_INPUT]->(i)
            RETURN i
        """

        with self.get_session() as session:
            result = session.run(
                query,
                input_id=input_id,
                student_id=student_id,
                date=date,
                content=content,
                category=category,
                teacher_id=teacher_id,
                created_at=datetime.now().isoformat()
            )
            return result.single() is not None

    def get_student_daily_inputs(
        self,
        student_id: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        학생의 Daily Input 목록 조회

        Args:
            student_id: 학생 ID
            limit: 조회 개수

        Returns:
            Daily Input 목록
        """
        query = """
            MATCH (s:Student {student_id: $student_id})-[:HAS_INPUT]->(i:DailyInput)
            RETURN i, s.name as student_name
            ORDER BY i.date DESC, i.created_at DESC
            LIMIT $limit
        """

        with self.get_session() as session:
            results = session.run(query, student_id=student_id, limit=limit)
            inputs = []

            for record in results:
                input_node = record["i"]
                input_data = dict(input_node)
                input_data["student_name"] = record["student_name"]
                inputs.append(input_data)

            return inputs

    def get_teacher_students(
        self,
        teacher_id: str
    ) -> List[Dict[str, Any]]:
        """
        선생님의 담당 학생 목록 조회

        Args:
            teacher_id: 선생님 ID

        Returns:
            학생 목록
        """
        # 실제 구현에서는 Teacher-Class-Student 관계를 사용해야 함
        # 현재는 간단하게 모든 학생을 반환
        query = """
            MATCH (s:Student)
            RETURN s
            ORDER BY s.student_id
            LIMIT 50
        """

        with self.get_session() as session:
            results = session.run(query)
            students = []

            for record in results:
                student_node = record["s"]
                student = dict(student_node)

                # 임베딩 제거
                student.pop("student_embedding", None)

                students.append(student)

            return students
