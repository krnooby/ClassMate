# -*- coding: utf-8 -*-
"""
Audio Router
오디오 파일 관리 API
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services.audio_session_service import AudioSessionService

router = APIRouter()


class CleanupRequest(BaseModel):
    """오디오 정리 요청"""
    session_id: str


class CleanupResponse(BaseModel):
    """오디오 정리 응답"""
    success: bool
    deleted_count: int
    message: str


@router.post("/cleanup-session-audio", response_model=CleanupResponse)
async def cleanup_session_audio(request: CleanupRequest):
    """
    세션의 모든 오디오 파일 삭제

    - **session_id**: 세션 ID (학생 ID + 세션 번호)

    Returns:
        삭제된 파일 수
    """
    try:
        audio_service = AudioSessionService.get_instance()
        deleted_count = audio_service.cleanup_session(request.session_id)

        return CleanupResponse(
            success=True,
            deleted_count=deleted_count,
            message=f"Successfully deleted {deleted_count} audio files"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup audio files: {str(e)}"
        )


@router.post("/cleanup-all-orphaned", response_model=CleanupResponse)
async def cleanup_orphaned_audio():
    """
    추적되지 않는 모든 오디오 파일 삭제 (관리자용)

    Returns:
        삭제된 파일 수
    """
    try:
        audio_service = AudioSessionService.get_instance()
        deleted_count = audio_service.cleanup_all_orphaned()

        return CleanupResponse(
            success=True,
            deleted_count=deleted_count,
            message=f"Successfully deleted {deleted_count} orphaned audio files"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup orphaned audio files: {str(e)}"
        )


@router.get("/session-audio/{session_id}")
async def get_session_audio(session_id: str):
    """
    세션의 오디오 파일 목록 조회

    - **session_id**: 세션 ID

    Returns:
        오디오 파일 목록
    """
    try:
        audio_service = AudioSessionService.get_instance()
        audio_files = audio_service.get_session_audio(session_id)

        return {
            "session_id": session_id,
            "audio_files": audio_files,
            "count": len(audio_files)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session audio: {str(e)}"
        )
