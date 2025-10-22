# -*- coding: utf-8 -*-
"""
Chat Router
AI 챗봇 상담 API 엔드포인트
"""
from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
import os
from openai import OpenAI
from api.services.graph_rag_service import get_graph_rag_service
from api.services.student_agent_service import get_student_agent_service
from api.prompts import PromptManager

router = APIRouter()


class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """채팅 요청"""
    student_id: str
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    """채팅 응답"""
    message: str
    student_context: str | None = None


@router.post("/student", response_model=ChatResponse)
async def chat_with_student(request: ChatRequest):
    """
    학생 맞춤 AI 상담 챗봇 (ReAct 에이전트)

    - student_id: 로그인한 학생 ID
    - messages: 대화 히스토리 (멀티턴)

    Returns:
        AI 상담 응답 (에이전트가 적절한 도구 선택 및 실행)
    """
    try:
        # 최신 사용자 메시지 가져오기
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        user_message = request.messages[-1].content

        # ReAct 에이전트로 처리
        agent_service = get_student_agent_service()
        response = agent_service.chat(
            student_id=request.student_id,
            message=user_message,
            chat_history=[msg.model_dump() for msg in request.messages[:-1]]
        )

        return ChatResponse(
            message=response,
            student_context=None  # 에이전트가 필요시 자동으로 조회
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/student-legacy", response_model=ChatResponse)
async def chat_with_student_legacy(request: ChatRequest):
    """
    학생 맞춤 AI 상담 챗봇 (기존 방식 - 백업용)

    - student_id: 로그인한 학생 ID
    - messages: 대화 히스토리 (멀티턴)

    Returns:
        AI 상담 응답
    """
    try:
        # 1. GraphRAG를 사용해보기 (Neo4j 사용 가능하면)
        use_graphrag = False
        rag_context = ""
        student_name = ""

        # 사용자의 최신 메시지를 쿼리로 사용 (벡터 검색용)
        query_text = ""
        if request.messages:
            query_text = request.messages[-1].content  # 최신 사용자 메시지

        try:
            graph_rag_service = get_graph_rag_service()
            rag_context = graph_rag_service.get_rag_context(
                student_id=request.student_id,
                query_text=query_text,
                use_vector_search=True  # 벡터 검색 사용
            )

            if rag_context:
                use_graphrag = True
                # 학생 이름 추출 (RAG 컨텍스트에서)
                import re
                name_match = re.search(r'이름: (.+)', rag_context)
                if name_match:
                    student_name = name_match.group(1)

                print(f"✅ GraphRAG 사용 (student: {request.student_id})")

            # 문제 추천 키워드 감지
            problem_keywords = ['문제', '문제 내줘', '문제 추천', '문제 풀래', '연습 문제',
                               'problem', 'practice', 'quiz', 'exercise']
            if any(keyword in query_text.lower() for keyword in problem_keywords):
                # 학생 약점에 맞는 문제 추천
                problems = graph_rag_service.search_problems_for_student(
                    student_id=request.student_id,
                    limit=3
                )

                if problems:
                    # RAG 컨텍스트에 문제 추가 (코드 블록으로 감싸서 GPT가 수정하지 못하게)
                    rag_context += "\n\n**📝 추천 문제 (학생 약점 기반):**\n"
                    rag_context += "```english-problems\n"
                    for i, p in enumerate(problems, 1):
                        area_name = {'RD': 'Reading', 'GR': 'Grammar', 'WR': 'Writing', 'LS': 'Listening', 'VO': 'Vocabulary'}
                        area_en = area_name.get(p['area'], p['area'])

                        rag_context += f"Problem {i} [{area_en}]:\n"
                        rag_context += f"{p['stem']}\n"
                        if p['options']:
                            for j, opt in enumerate(p['options'], 1):
                                rag_context += f"   {j}) {opt}\n"
                        rag_context += f"Answer: {p['answer']}\n\n"

                    rag_context += "```\n"
                    print(f"✅ 문제 추천: {len(problems)}개")

        except Exception as e:
            print(f"⚠️  GraphRAG 사용 불가, JSON 폴백 사용: {e}")
            use_graphrag = False

        # 2. GraphRAG 실패 시 JSON 폴백
        if not use_graphrag:
            students_file = Path("/home/sh/projects/ClassMate/data/json/students_rag.json")
            class_file = Path("/home/sh/projects/ClassMate/data/json/class.json")

            # 학생 데이터 로드
            with open(students_file, "r", encoding="utf-8") as f:
                students_data = json.load(f)

            # 해당 학생 찾기
            student_summary = None
            student_raw = None
            for s in students_data:
                original = s.get("원본데이터", {})
                if original.get("student_id") == request.student_id:
                    student_summary = s.get("자연어요약", "")
                    student_raw = original
                    break

            if not student_raw:
                raise HTTPException(status_code=404, detail=f"Student not found: {request.student_id}")

            student_name = student_raw['name']

            # 반 정보 로드
            with open(class_file, "r", encoding="utf-8") as f:
                classes_data = json.load(f)

            class_info = None
            for c in classes_data:
                if c.get("class_id") == student_raw.get("class_id"):
                    class_info = c
                    break

            # JSON 기반 컨텍스트 생성
            rag_context = f"""**{student_raw['name']} 학생의 학습 현황:**
{student_summary}

**수업 정보:**
- 반: {class_info.get('class_name') if class_info else 'N/A'}반
- 수업 일정: {class_info.get('schedule') if class_info else 'N/A'}
- 지금 배우는 내용: {class_info.get('progress') if class_info else 'N/A'}
- 이번 숙제: {class_info.get('homework') if class_info else 'N/A'}
- 이번 달 시험: {class_info.get('monthly_test') if class_info else 'N/A'}"""

        # 3. PromptManager를 사용해 학생용 시스템 프롬프트 생성
        system_prompt = PromptManager.get_system_prompt(
            role="student",
            model="gpt-4.1-mini",
            context={
                "student_name": student_name,
                "rag_context": rag_context
            }
        )

        # 4. OpenAI API 호출 (환경 변수에서 API 키 가져오기)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # API 키가 없으면 목업 응답 반환
            return ChatResponse(
                message="안녕하세요! AI 상담을 위해서는 OpenAI API 키가 필요합니다. 관리자에게 문의해주세요.",
                student_context=rag_context
            )

        client = OpenAI(api_key=api_key)

        # 메시지 히스토리 구성
        messages = [{"role": "system", "content": system_prompt}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        # OpenAI API 호출 (GPT-4.1 Mini - 빠른 인텔리전스 모델)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        assistant_message = response.choices[0].message.content

        return ChatResponse(
            message=assistant_message,
            student_context=rag_context if len(request.messages) == 1 else None
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Data file not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/parent", response_model=ChatResponse)
async def chat_with_parent(request: ChatRequest):
    """
    학부모 맞춤 AI 상담 챗봇

    - student_id: 자녀의 학생 ID
    - messages: 대화 히스토리 (멀티턴)

    Returns:
        AI 상담 응답
    """
    try:
        # 1. GraphRAG를 사용해보기 (Neo4j 사용 가능하면)
        use_graphrag = False
        rag_context = ""
        student_name = ""

        # 사용자의 최신 메시지를 쿼리로 사용 (벡터 검색용)
        query_text = ""
        if request.messages:
            query_text = request.messages[-1].content

        try:
            graph_rag_service = get_graph_rag_service()
            rag_context = graph_rag_service.get_rag_context(
                student_id=request.student_id,
                query_text=query_text,
                use_vector_search=True
            )

            if rag_context:
                use_graphrag = True
                import re
                name_match = re.search(r'이름: (.+)', rag_context)
                if name_match:
                    student_name = name_match.group(1)

                print(f"✅ GraphRAG 사용 (parent, student: {request.student_id})")
        except Exception as e:
            print(f"⚠️  GraphRAG 사용 불가, JSON 폴백 사용: {e}")
            use_graphrag = False

        # 2. GraphRAG 실패 시 JSON 폴백
        student_raw = None
        if not use_graphrag:
            students_file = Path("/home/sh/projects/ClassMate/data/json/students_rag.json")
            class_file = Path("/home/sh/projects/ClassMate/data/json/class.json")

            # 학생 데이터 로드
            with open(students_file, "r", encoding="utf-8") as f:
                students_data = json.load(f)

            # 해당 학생 찾기
            student_summary = None
            for s in students_data:
                original = s.get("원본데이터", {})
                if original.get("student_id") == request.student_id:
                    student_summary = s.get("자연어요약", "")
                    student_raw = original
                    break

            if not student_raw:
                raise HTTPException(status_code=404, detail=f"Student not found: {request.student_id}")

            student_name = student_raw['name']

            # 반 정보 로드
            with open(class_file, "r", encoding="utf-8") as f:
                classes_data = json.load(f)

            class_info = None
            for c in classes_data:
                if c.get("class_id") == student_raw.get("class_id"):
                    class_info = c
                    break

            # 상세 성적 정보 준비
            assessment = student_raw.get("assessment", {})
            radar_scores = assessment.get("radar_scores", {})
            overall = assessment.get("overall", {})
            attendance = student_raw.get("attendance", {})
            homework = student_raw.get("homework", {})
            notes = student_raw.get("notes", {})

            # JSON 기반 상세 컨텍스트 생성 (학부모용)
            rag_context = f"""**{student_raw['name']} 학생의 종합 학습 현황:**
{student_summary}

**상세 성적 데이터:**
- CEFR 레벨: {overall.get('cefr', 'N/A')}
- 전체 백분위: {overall.get('percentile_rank', 'N/A')}위
- 영역별 점수:
  * 문법(Grammar): {radar_scores.get('grammar', 'N/A')}점
  * 어휘(Vocabulary): {radar_scores.get('vocabulary', 'N/A')}점
  * 독해(Reading): {radar_scores.get('reading', 'N/A')}점
  * 듣기(Listening): {radar_scores.get('listening', 'N/A')}점
  * 쓰기(Writing): {radar_scores.get('writing', 'N/A')}점

**출결 및 학습 태도:**
- 출석률: {attendance.get('total_sessions', 0) - attendance.get('absent', 0)}/{attendance.get('total_sessions', 0)}회 출석
- 숙제 완료율: {homework.get('assigned', 0) - homework.get('missed', 0)}/{homework.get('assigned', 0)}건 제출
- 학습 태도: {notes.get('attitude', '양호')}
- 학교 평가: {notes.get('school_exam_level', 'N/A')}

**수업 정보:**
- 담당 반: {class_info.get('class_name') if class_info else 'N/A'}반
- 수업 일정: {class_info.get('schedule') if class_info else 'N/A'}
- 현재 진도: {class_info.get('progress') if class_info else 'N/A'}
- 이번 숙제: {class_info.get('homework') if class_info else 'N/A'}
- 이번 달 시험: {class_info.get('monthly_test') if class_info else 'N/A'}"""

        # 3. PromptManager를 사용해 학부모용 시스템 프롬프트 생성
        system_prompt = PromptManager.get_system_prompt(
            role="parent",
            model="gpt-4.1-mini",
            context={"rag_context": rag_context}
        )

        # 4. OpenAI API 호출
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ChatResponse(
                message="안녕하세요 학부모님. AI 상담을 위해서는 OpenAI API 키가 필요합니다. 관리자에게 문의해주세요.",
                student_context=rag_context
            )

        client = OpenAI(api_key=api_key)

        # 메시지 히스토리 구성
        messages = [{"role": "system", "content": system_prompt}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        # OpenAI API 호출 (GPT-4.1 Mini - 빠른 인텔리전스 모델)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=600
        )

        assistant_message = response.choices[0].message.content

        return ChatResponse(
            message=assistant_message,
            student_context=rag_context if len(request.messages) == 1 else None
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Data file not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
