# -*- coding: utf-8 -*-
"""
Teacher Chat Router
선생님용 AI 챗봇 엔드포인트
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from teacher.services.teacher_agent_service import get_teacher_agent_service

router = APIRouter()


class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """채팅 요청"""
    teacher_id: str
    messages: List[ChatMessage]


class ModelInfo(BaseModel):
    """모델 정보"""
    primary: str
    all_used: List[str]


class ChatResponse(BaseModel):
    """채팅 응답"""
    message: str
    model_info: ModelInfo | None = None
    ui_panel: Optional[str] = None  # "exam_upload", "daily_input", or None
    ui_data: Optional[Dict[str, Any]] = None  # UI 패널에 전달할 데이터


@router.post("/teacher", response_model=ChatResponse)
async def chat_with_teacher(request: ChatRequest):
    """
    선생님 맞춤 AI 업무 지원 챗봇 (Function Calling)

    - teacher_id: 로그인한 선생님 ID
    - messages: 대화 히스토리 (멀티턴)

    Returns:
        AI 응답 + UI 패널 트리거 정보
    """
    try:
        # 최신 사용자 메시지 가져오기
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        user_message = request.messages[-1].content

        # Function Calling 에이전트로 처리
        agent_service = get_teacher_agent_service()
        response = agent_service.chat(
            teacher_id=request.teacher_id,
            message=user_message,
            chat_history=[msg.model_dump() for msg in request.messages[:-1]]
        )

        # response contains: message, model_info, and optionally ui_panel + ui_data
        return ChatResponse(
            message=response["message"],
            model_info=ModelInfo(**response["model_info"]),
            ui_panel=response.get("ui_panel"),
            ui_data=response.get("ui_data")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
