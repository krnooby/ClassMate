# -*- coding: utf-8 -*-
"""
Student Chat Router
학생용 AI 챗봇 엔드포인트
"""
from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
import os
from openai import OpenAI
from shared.services import get_graph_rag_service
from student.services import get_student_agent_service
from shared.prompts import PromptManager

router = APIRouter()


class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """채팅 요청"""
    student_id: str
    messages: List[ChatMessage]


class ModelInfo(BaseModel):
    """모델 정보"""
    primary: str
    all_used: List[str]


class QuickReply(BaseModel):
    """빠른 응답 버튼"""
    label: str  # 버튼에 표시될 텍스트
    value: str  # 클릭 시 전송될 메시지


class ChatResponse(BaseModel):
    """채팅 응답"""
    message: str
    student_context: str | None = None
    model_info: ModelInfo | None = None
    quick_replies: List[QuickReply] | None = None


@router.post("/student", response_model=ChatResponse)
async def chat_with_student(request: ChatRequest):
    """
    학생 맞춤 AI 상담 챗봇 (Function Calling)

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

        # Function Calling 에이전트로 처리
        agent_service = get_student_agent_service()
        response = agent_service.chat(
            student_id=request.student_id,
            message=user_message,
            chat_history=[msg.model_dump() for msg in request.messages[:-1]]
        )

        # response is now a dict with 'message', 'model_info', and optionally 'quick_replies'
        quick_replies = None
        if "quick_replies" in response:
            quick_replies = [QuickReply(**qr) for qr in response["quick_replies"]]

        return ChatResponse(
            message=response["message"],
            student_context=None,  # 에이전트가 필요시 자동으로 조회
            model_info=ModelInfo(**response["model_info"]),
            quick_replies=quick_replies
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/student-legacy", response_model=ChatResponse)
async def chat_with_student_legacy(request: ChatRequest):
    """
    학생 맞춤 AI 상담 챗봇 (레거시 방식)

    - student_id: 로그인한 학생 ID
    - messages: 대화 히스토리 (멀티턴)

    Returns:
        AI 상담 응답
    """
    try:
        # 1. GraphRAG 사용
        use_graphrag = False
        rag_context = ""
        student_name = ""

        # 사용자의 최신 메시지를 쿼리로 사용
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

                print(f"✅ GraphRAG 사용 (student: {request.student_id})")

            # 문제 추천 키워드 감지
            problem_keywords = ['문제', '문제 내줘', '문제 추천', '문제 풀래', '연습 문제',
                               'problem', 'practice', 'quiz', 'exercise']
            if any(keyword in query_text.lower() for keyword in problem_keywords):
                problems = graph_rag_service.search_problems_for_student(
                    student_id=request.student_id,
                    limit=3
                )

                if problems:
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

            with open(students_file, "r", encoding="utf-8") as f:
                students_data = json.load(f)

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

            with open(class_file, "r", encoding="utf-8") as f:
                classes_data = json.load(f)

            class_info = None
            for c in classes_data:
                if c.get("class_id") == student_raw.get("class_id"):
                    class_info = c
                    break

            rag_context = f"""**{student_raw['name']} 학생의 학습 현황:**
{student_summary}

**수업 정보:**
- 반: {class_info.get('class_name') if class_info else 'N/A'}반
- 수업 일정: {class_info.get('schedule') if class_info else 'N/A'}
- 지금 배우는 내용: {class_info.get('progress') if class_info else 'N/A'}
- 이번 숙제: {class_info.get('homework') if class_info else 'N/A'}
- 이번 달 시험: {class_info.get('monthly_test') if class_info else 'N/A'}"""

        # 3. PromptManager로 시스템 프롬프트 생성
        system_prompt = PromptManager.get_system_prompt(
            role="student",
            model="gpt-4.1-mini",
            context={
                "student_name": student_name,
                "rag_context": rag_context
            }
        )

        # 4. OpenAI API 호출
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ChatResponse(
                message="안녕하세요! AI 상담을 위해서는 OpenAI API 키가 필요합니다. 관리자에게 문의해주세요.",
                student_context=rag_context
            )

        client = OpenAI(api_key=api_key)

        messages = [{"role": "system", "content": system_prompt}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

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
