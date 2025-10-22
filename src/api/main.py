# -*- coding: utf-8 -*-
"""
FastAPI 백엔드 메인 애플리케이션

ClassMate - 영어 시험 문제 자동화 플랫폼
기존 CLI 기반 teacher 모듈을 웹 인터페이스로 확장
"""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from pathlib import Path
from dotenv import load_dotenv

from api.services.neo4j_service import Neo4jService

# 환경 변수 로드
load_dotenv()


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 코드"""
    # Startup
    print("🚀 ClassMate API Server Starting...")

    # Neo4j 연결 테스트
    neo4j_service = Neo4jService.get_instance()
    if neo4j_service.test_connection():
        print("✅ Neo4j connection successful")
    else:
        print("❌ Neo4j connection failed")

    yield

    # Shutdown
    print("🛑 ClassMate API Server Shutting down...")
    neo4j_service.close()


# FastAPI 앱 초기화
app = FastAPI(
    title="ClassMate API",
    description="영어 시험 문제 자동화 플랫폼 API",
    version="1.0.0",
    lifespan=lifespan
)


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React 개발 서버
        "http://localhost:5173",  # Vite 개발 서버
        "http://localhost:5174",  # Vite 개발 서버 (포트 충돌 시)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Static file serving (TTS 음성 파일 및 효과음)
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    print(f"✅ Static files mounted at /static from {static_dir}")
else:
    print(f"⚠️  Static directory not found: {static_dir}")


# Health check endpoint
@app.get("/")
async def root():
    """루트 엔드포인트 - 서버 상태 확인"""
    return {
        "status": "ok",
        "message": "ClassMate API Server is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    neo4j_service = Neo4jService.get_instance()
    neo4j_status = neo4j_service.test_connection()

    return {
        "status": "healthy" if neo4j_status else "unhealthy",
        "services": {
            "neo4j": "connected" if neo4j_status else "disconnected"
        }
    }


# 라우터 등록
from api.routers import students, problems, teachers, parents, dashboard, classes, auth, chat

app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI챗봇"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["대시보드"])
app.include_router(students.router, prefix="/api/students", tags=["학생"])
app.include_router(problems.router, prefix="/api/problems", tags=["문제"])
app.include_router(teachers.router, prefix="/api/teachers", tags=["선생님"])
app.include_router(parents.router, prefix="/api/parents", tags=["학부모"])
app.include_router(classes.router, prefix="/api/classes", tags=["반"])


if __name__ == "__main__":
    import uvicorn

    # 개발 서버 실행
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
