# -*- coding: utf-8 -*-
"""
GraphRAG Service
Neo4j 벡터 검색 + 그래프 탐색을 통한 RAG 구현
"""
from __future__ import annotations
import os
from typing import List, Dict, Any
from openai import OpenAI
from neo4j import GraphDatabase


class GraphRAGService:
    """GraphRAG 서비스"""

    def __init__(self):
        """초기화"""
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_user = os.getenv("NEO4J_USERNAME")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")
        self.neo4j_db = os.getenv("NEO4J_DB", "neo4j")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Neo4j 드라이버 (lazy initialization)
        self._driver = None

    def _get_driver(self):
        """Neo4j 드라이버 가져오기 (싱글톤)"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
        return self._driver

    def close(self):
        """연결 종료"""
        if self._driver:
            self._driver.close()
            self._driver = None

    def get_embedding(self, text: str) -> List[float]:
        """
        텍스트를 임베딩 벡터로 변환
        Neo4j에 저장된 Qwen3 임베딩과 호환되도록 동일한 모델 사용

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (1024 dimensions for Qwen3-Embedding-0.6B)
        """
        import torch
        from transformers import AutoTokenizer, AutoModel

        model_name = os.getenv("EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B")

        # 모델 캐싱 (재사용)
        if not hasattr(self, '_tokenizer'):
            self._tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            use_fp16 = torch.cuda.is_available()
            self._model = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if use_fp16 else torch.float32
            )
            self._model.eval()
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model.to(self._device)

        # 임베딩 생성
        with torch.no_grad():
            tok = self._tokenizer([text], padding=True, truncation=True, max_length=512, return_tensors="pt")
            tok = {k: v.to(self._device) for k, v in tok.items()}
            out = self._model(**tok)

            if hasattr(out, "pooler_output") and out.pooler_output is not None:
                emb = out.pooler_output
            else:
                last = out.last_hidden_state
                attn = tok["attention_mask"].unsqueeze(-1)
                emb = (last * attn).sum(dim=1) / attn.sum(dim=1).clamp(min=1)

            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
            return emb.cpu().to(torch.float32).tolist()[0]

    def vector_search_students(
        self,
        query_text: str,
        student_id: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        벡터 유사도 검색으로 관련 학생 정보 찾기

        Args:
            query_text: 검색 쿼리
            student_id: 특정 학생 ID (None이면 모든 학생 검색)
            limit: 결과 개수

        Returns:
            관련 학생 정보 리스트 (유사도 점수 포함)
        """
        # 쿼리 임베딩 생성
        query_embedding = self.get_embedding(query_text)

        driver = self._get_driver()

        with driver.session(database=self.neo4j_db) as session:
            # 벡터 유사도 검색 쿼리
            if student_id:
                # 특정 학생만 검색
                cypher = """
                MATCH (s:Student {student_id: $student_id})
                WHERE s.embedding IS NOT NULL
                WITH s,
                     vector.similarity.cosine(s.embedding, $query_embedding) AS score
                WHERE score > 0.7
                RETURN s.student_id as student_id,
                       s.name as name,
                       s.summary_ko as summary,
                       s.strong_area as strong_area,
                       s.weak_area as weak_area,
                       score
                ORDER BY score DESC
                LIMIT $limit
                """
            else:
                # 모든 학생 검색
                cypher = """
                MATCH (s:Student)
                WHERE s.embedding IS NOT NULL
                WITH s,
                     vector.similarity.cosine(s.embedding, $query_embedding) AS score
                WHERE score > 0.7
                RETURN s.student_id as student_id,
                       s.name as name,
                       s.summary_ko as summary,
                       s.strong_area as strong_area,
                       s.weak_area as weak_area,
                       score
                ORDER BY score DESC
                LIMIT $limit
                """

            result = session.run(
                cypher,
                query_embedding=query_embedding,
                student_id=student_id,
                limit=limit
            )

            return [dict(record) for record in result]

    def get_student_graph_context(self, student_id: str) -> Dict[str, Any]:
        """
        그래프 탐색으로 학생 관련 컨텍스트 가져오기
        (같은 반, 선생님, 과제, 성적 등)

        Args:
            student_id: 학생 ID

        Returns:
            학생 관련 그래프 컨텍스트
        """
        driver = self._get_driver()

        with driver.session(database=self.neo4j_db) as session:
            cypher = """
            // 학생 기본 정보
            MATCH (s:Student {student_id: $student_id})

            // 성적 정보
            OPTIONAL MATCH (s)-[:HAS_ASSESSMENT]->(assess:Assessment)

            // 출석 정보
            OPTIONAL MATCH (s)-[:HAS_ATTENDANCE]->(attend:Attendance)

            // 숙제 정보
            OPTIONAL MATCH (s)-[:HAS_HOMEWORK]->(hw:Homework)

            // 레이더 점수
            OPTIONAL MATCH (s)-[:HAS_RADAR]->(radar:RadarScores)

            // 같은 반 정보
            OPTIONAL MATCH (s)-[:ENROLLED_IN]->(c:Class)
            OPTIONAL MATCH (c)<-[:TEACHES]-(t:Teacher)

            // 같은 반 학생들 (성적 비교용)
            OPTIONAL MATCH (c)<-[:ENROLLED_IN]-(peer:Student)
            OPTIONAL MATCH (peer)-[:HAS_ASSESSMENT]->(peer_assess:Assessment)
            WHERE peer.student_id <> s.student_id

            RETURN s {
                .student_id, .name, .grade_code, .grade_label,
                .summary_ko, .strong_area, .weak_area
            } as student,
            assess {.cefr, .percentile_rank} as assessment,
            attend {.total_sessions, .absent} as attendance,
            hw {.assigned, .missed} as homework,
            radar {.grammar, .vocabulary, .reading, .listening, .writing} as radar_scores,
            c {.class_id, .class_name, .schedule, .progress, .homework} as class,
            t {.teacher_id, .name} as teacher,
            collect(DISTINCT peer {
                .student_id, .name,
                cefr: peer_assess.cefr,
                percentile: peer_assess.percentile_rank
            })[0..5] as peers
            """

            result = session.run(cypher, student_id=student_id)
            record = result.single()

            if not record:
                return {}

            return {
                "student": dict(record["student"]) if record["student"] else {},
                "assessment": dict(record["assessment"]) if record["assessment"] else {},
                "attendance": dict(record["attendance"]) if record["attendance"] else {},
                "homework": dict(record["homework"]) if record["homework"] else {},
                "radar_scores": dict(record["radar_scores"]) if record["radar_scores"] else {},
                "class": dict(record["class"]) if record["class"] else {},
                "teacher": dict(record["teacher"]) if record["teacher"] else {},
                "peers": [dict(p) for p in record["peers"] if p] if record["peers"] else []
            }

    def get_rag_context(
        self,
        student_id: str,
        query_text: str,
        use_vector_search: bool = True
    ) -> str:
        """
        RAG용 컨텍스트 생성
        벡터 검색 + 그래프 탐색 결과를 텍스트로 조합

        Args:
            student_id: 학생 ID
            query_text: 사용자 질문
            use_vector_search: 벡터 검색 사용 여부

        Returns:
            RAG용 컨텍스트 텍스트
        """
        context_parts = []

        # 1. 그래프 탐색으로 학생 정보 가져오기
        graph_context = self.get_student_graph_context(student_id)

        if graph_context.get("student"):
            student = graph_context["student"]
            assessment = graph_context.get("assessment", {})
            attendance = graph_context.get("attendance", {})
            homework = graph_context.get("homework", {})
            radar = graph_context.get("radar_scores", {})

            # 출석률 계산
            total_sessions = attendance.get('total_sessions', 0)
            absent = attendance.get('absent', 0)
            attendance_rate = ((total_sessions - absent) / total_sessions * 100) if total_sessions > 0 else 0

            # 숙제 완료율 계산
            hw_assigned = homework.get('assigned', 0)
            hw_missed = homework.get('missed', 0)
            hw_rate = ((hw_assigned - hw_missed) / hw_assigned * 100) if hw_assigned > 0 else 0

            context_parts.append(f"""
**학생 기본 정보:**
- 이름: {student.get('name')}
- 학년: {student.get('grade_label')}
- CEFR 레벨: {assessment.get('cefr', 'N/A')}
- 백분위: {assessment.get('percentile_rank', 'N/A')}위
- 출석률: {attendance_rate:.1f}% ({total_sessions - absent}/{total_sessions}회 출석)
- 숙제 완료율: {hw_rate:.1f}% ({hw_assigned - hw_missed}/{hw_assigned}개 제출)

**강점/약점:**
- 강점: {student.get('strong_area', 'N/A')}
- 약점: {student.get('weak_area', 'N/A')}

**영역별 점수:**
- 문법: {radar.get('grammar', 'N/A')}점
- 어휘: {radar.get('vocabulary', 'N/A')}점
- 독해: {radar.get('reading', 'N/A')}점
- 듣기: {radar.get('listening', 'N/A')}점
- 쓰기: {radar.get('writing', 'N/A')}점
""")

        if graph_context.get("class"):
            cls = graph_context["class"]
            context_parts.append(f"""
**반 정보:**
- 반: {cls.get('class_name')}반
- 수업 일정: {cls.get('schedule', 'N/A')}
- 현재 진도: {cls.get('progress', 'N/A')}
- 이번 숙제: {cls.get('homework', 'N/A')}
""")

        if graph_context.get("teacher"):
            teacher = graph_context["teacher"]
            context_parts.append(f"""
**담당 선생님:** {teacher.get('name', 'N/A')}
""")

        # 2. 벡터 검색으로 유사한 내용 찾기 (선택적)
        if use_vector_search:
            try:
                vector_results = self.vector_search_students(
                    query_text=query_text,
                    student_id=student_id,
                    limit=3
                )

                if vector_results:
                    context_parts.append("\n**관련 학습 기록:**")
                    for idx, result in enumerate(vector_results, 1):
                        summary = result.get('summary', '')
                        context_parts.append(
                            f"{idx}. {summary} (관련도: {result['score']:.2f})"
                        )
            except Exception as e:
                # 벡터 검색 실패해도 그래프 컨텍스트는 사용
                print(f"Vector search failed: {e}")

        # 3. 동료 학생 정보 (성적 비교용)
        if graph_context.get("peers"):
            peers = graph_context["peers"]
            valid_peers = [p for p in peers if p.get('name')]
            if valid_peers:
                context_parts.append("\n**같은 반 친구들:**")
                for peer in valid_peers[:3]:
                    cefr = peer.get('cefr', 'N/A')
                    percentile = peer.get('percentile', 'N/A')
                    context_parts.append(
                        f"- {peer['name']}: {cefr} 레벨, {percentile}위"
                    )

        return "\n".join(context_parts)

    def _has_korean(self, text: str) -> bool:
        """Check if text contains Korean characters"""
        import re
        return bool(re.search('[가-힣]', str(text)))

    def search_problems_for_student(
        self,
        student_id: str,
        area: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        학생 약점에 맞는 문제 추천

        Args:
            student_id: 학생 ID
            area: 문제 영역 (RD=독해, GR=문법, WR=쓰기, LS=듣기, VO=어휘)
            limit: 문제 개수

        Returns:
            추천 문제 리스트 (영어 문제만)
        """
        driver = self._get_driver()

        with driver.session(database=self.neo4j_db) as session:
            # 학생 정보 조회
            student_info = session.run('''
                MATCH (s:Student {student_id: $student_id})
                OPTIONAL MATCH (s)-[:HAS_ASSESSMENT]->(a:Assessment)
                RETURN s.weak_area as weak_area, a.cefr as cefr
            ''', student_id=student_id).single()

            if not student_info:
                return []

            weak_area = student_info['weak_area']
            student_cefr = student_info['cefr'] or 'A1'

            # 영역 매핑 (한글 -> 영문 코드)
            area_map = {
                '독해': 'RD',
                'reading': 'RD',
                '문법': 'GR',
                'grammar': 'GR',
                '쓰기': 'WR',
                'writing': 'WR',
                '듣기': 'LS',
                'listening': 'LS',
                '어휘': 'VO',
                'vocabulary': 'VO'
            }

            # 영역 결정: 파라미터 > 약점
            target_area = None
            if area:
                target_area = area_map.get(area.lower(), area.upper())
            elif weak_area:
                target_area = area_map.get(weak_area, None)

            # 문제 검색 (한글 필터링을 위해 더 많이 가져옴)
            fetch_limit = limit * 3  # 한글 문제가 있을 수 있으니 여유있게

            if target_area:
                # 특정 영역 문제
                cypher = '''
                    MATCH (p:Problem)
                    WHERE p.area = $area
                      AND p.cefr = $cefr
                    OPTIONAL MATCH (p)-[:HAS_FIG]->(f:Fig)
                    OPTIONAL MATCH (p)-[:HAS_TABLE]->(t:Tbl)
                    WITH p,
                         collect(DISTINCT f) as figures,
                         collect(DISTINCT t) as tables
                    RETURN p.problem_id as problem_id,
                           p.stem as stem,
                           p.options as options,
                           p.answer as answer,
                           p.difficulty as difficulty,
                           p.cefr as cefr,
                           p.area as area,
                           p.type as type,
                           p.audio_url as audio_url,
                           p.audio_transcript as audio_transcript,
                           figures,
                           tables
                    ORDER BY rand()
                    LIMIT $fetch_limit
                '''
                result = session.run(cypher, area=target_area, cefr=student_cefr, fetch_limit=fetch_limit)
            else:
                # 전체 레벨에 맞는 문제
                cypher = '''
                    MATCH (p:Problem)
                    WHERE p.cefr = $cefr
                    OPTIONAL MATCH (p)-[:HAS_FIG]->(f:Fig)
                    OPTIONAL MATCH (p)-[:HAS_TABLE]->(t:Tbl)
                    WITH p,
                         collect(DISTINCT f) as figures,
                         collect(DISTINCT t) as tables
                    RETURN p.problem_id as problem_id,
                           p.stem as stem,
                           p.options as options,
                           p.answer as answer,
                           p.difficulty as difficulty,
                           p.cefr as cefr,
                           p.area as area,
                           p.type as type,
                           p.audio_url as audio_url,
                           p.audio_transcript as audio_transcript,
                           figures,
                           tables
                    ORDER BY rand()
                    LIMIT $fetch_limit
                '''
                result = session.run(cypher, cefr=student_cefr, fetch_limit=fetch_limit)

            # 한글 문제 필터링 및 Figure/Table 정보 추가
            all_problems = []
            for record in result:
                problem = dict(record)

                # Figure 정보 추가
                figures = [dict(f) for f in record['figures'] if f is not None]
                if figures:
                    problem['figures'] = [
                        {
                            'asset_id': f.get('asset_id'),
                            'public_url': f.get('public_url'),
                            'caption': f.get('caption'),
                            'storage_key': f.get('storage_key')
                        }
                        for f in figures
                        if f.get('public_url')  # public_url이 있는 것만
                    ]

                # Table 정보 추가
                tables = [dict(t) for t in record['tables'] if t is not None]
                if tables:
                    problem['tables'] = [
                        {
                            'table_id': t.get('table_id'),
                            'public_url': t.get('public_url'),
                            'title': t.get('title'),
                            'storage_key': t.get('storage_key')
                        }
                        for t in tables
                        if t.get('public_url')  # public_url이 있는 것만
                    ]

                all_problems.append(problem)

            english_problems = [
                p for p in all_problems
                if not self._has_korean(p.get('stem', ''))
            ]

            # 요청한 개수만큼만 반환
            return english_problems[:limit]


# 싱글톤 인스턴스
_graph_rag_service = None


def get_graph_rag_service() -> GraphRAGService:
    """GraphRAG 서비스 싱글톤 인스턴스 가져오기"""
    global _graph_rag_service
    if _graph_rag_service is None:
        _graph_rag_service = GraphRAGService()
    return _graph_rag_service
