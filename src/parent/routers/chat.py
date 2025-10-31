# -*- coding: utf-8 -*-
"""
Parent Chat Router
학부모용 AI 챗봇 엔드포인트 (Function Calling 기반)
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from parent.services import get_parent_agent_service

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
    """사용된 모델 정보"""
    primary: str
    all_used: List[str]


class QuickReply(BaseModel):
    """빠른 응답 버튼"""
    label: str
    value: str


class ChatResponse(BaseModel):
    """채팅 응답"""
    message: str
    model_info: ModelInfo
    quick_replies: Optional[List[QuickReply]] = None


@router.post("/parent", response_model=ChatResponse)
async def chat_with_parent(request: ChatRequest):
    """
    학부모 맞춤 AI 상담 챗봇 (Function Calling)

    - student_id: 자녀의 학생 ID
    - messages: 대화 히스토리 (멀티턴)

    Returns:
        AI 상담 응답 및 사용된 모델 정보

    기능:
        - 자녀의 학습 정보 조회
        - 성적 분석 및 추이
        - 맞춤형 학습 조언
        - 출석/숙제 현황
        - 개선 영역 추천
    """
    try:
        # ParentAgentService 사용
        agent_service = get_parent_agent_service()

        # 최신 메시지 추출
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages cannot be empty")

        latest_message = request.messages[-1].content

        # 이전 대화 히스토리 (최신 메시지 제외)
        chat_history = []
        for msg in request.messages[:-1]:
            chat_history.append({
                "role": msg.role,
                "content": msg.content
            })

        # Agent 서비스를 통해 응답 생성
        response_data = agent_service.chat(
            student_id=request.student_id,
            message=latest_message,
            chat_history=chat_history if chat_history else None
        )

        # Quick replies 처리
        quick_replies_data = response_data.get("quick_replies")
        quick_replies = None
        if quick_replies_data:
            quick_replies = [QuickReply(**qr) for qr in quick_replies_data]

        return ChatResponse(
            message=response_data["message"],
            model_info=ModelInfo(
                primary=response_data["model_info"]["primary"],
                all_used=response_data["model_info"]["all_used"]
            ),
            quick_replies=quick_replies
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
