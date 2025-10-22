# 📚 ClassMate

> AI 기반 영어 학원 맞춤형 학습 관리 시스템

**ClassMate**는 선생님, 학생, 학부모를 위한 올인원 학습 관리 플랫폼입니다. GraphRAG와 Neo4j를 활용하여 개인화된 학습 경험을 제공합니다.

<br/>

## ✨ 주요 기능

### 👨‍🏫 선생님
- **📝 학생 기록 관리** - 출석, 숙제, 영역별 점수 관리
- **📊 학급 대시보드** - 전체 학생 학습 현황 한눈에 파악
- **🤖 AI 학습 상담** - 학생별 맞춤 조언

### 👨‍🎓 학생
- **💬 AI 튜터 챗봇** - 실시간 학습 코칭 및 문제 추천
- **🎯 맞춤형 문제 풀이** - CEFR 레벨 기반 문제 자동 추천
- **📈 학습 대시보드** - Area별 성취도 및 진도 확인
- **🔊 리스닝 문제** - TTS 기반 듣기 평가

### 👪 학부모
- **👀 자녀 학습 모니터링** - 실시간 학습 현황 확인
- **💬 AI 상담** - 자녀 학습 분석 및 조언
- **📊 성적 분석** - 영역별 강/약점 리포트

<br/>

## 🏗️ 기술 스택

### Frontend
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

### Backend
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)

### AI/ML
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![GPT-4](https://img.shields.io/badge/GPT--4.1--mini-74aa9c?style=for-the-badge&logo=openai&logoColor=white)

- **GPT-4.1-mini** - AI Agent (Function Calling)
- **o4-mini** - 문제 생성 (추론 특화)
- **Qwen3** - 임베딩 (1024D)
- **GraphRAG** - 컨텍스트 검색

<br/>

## 🚀 빠른 시작

### Prerequisites
- Python 3.10+
- Node.js 18+
- Neo4j Database
- OpenAI API Key

### Installation

```bash
# 1. 저장소 클론
git clone https://github.com/krnooby/ClassMate.git
cd ClassMate

# 2. 백엔드 설정
pip install -r requirements.txt
cp .env.example .env  # API 키 설정

# 3. 프론트엔드 설정
cd src/web
npm install
```

### Run

```bash
# 백엔드 서버 실행 (터미널 1)
PYTHONPATH=./src python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 프론트엔드 서버 실행 (터미널 2)
cd src/web
npm run dev
```

**접속:** http://localhost:5173

### 로그인 정보

| 역할 | ID | Password |
|------|-----|----------|
| 학생 | S-01 | test |
| 선생님 | T-01 | teacher |
| 학부모 | P-01 | parent |

<br/>

## 📁 프로젝트 구조

```
ClassMate/
├── src/
│   ├── api/                 # FastAPI 백엔드
│   │   ├── main.py         # 메인 애플리케이션
│   │   ├── routers/        # API 엔드포인트
│   │   └── services/       # 비즈니스 로직
│   │
│   ├── web/                # React 프론트엔드
│   │   ├── src/
│   │   │   ├── pages/     # 페이지 컴포넌트
│   │   │   ├── components/ # 재사용 컴포넌트
│   │   │   └── api/       # API 클라이언트
│   │   └── package.json
│   │
│   ├── student/            # 학생 AI 에이전트
│   ├── teacher/            # 선생님 서비스
│   ├── parent/             # 학부모 서비스
│   └── shared/             # 공통 유틸리티
│
├── static/                 # 정적 파일
│   ├── audio/             # 리스닝 오디오 (TTS)
│   └── effects/           # 사운드 효과
│
└── requirements.txt        # Python 패키지
```

<br/>

## 🎯 핵심 기술

### GraphRAG + Neo4j
- 학생 데이터, 문제, 커리큘럼을 그래프로 모델링
- 벡터 검색으로 맞춤형 컨텍스트 제공
- 실시간 관계 추론

### Function Calling Agent
- GPT-4.1-mini 기반 멀티 에이전트 시스템
- 학생/선생님/학부모별 특화 도구
- 동적 문제 추천 및 생성

### Real-time TTS
- Google Cloud TTS 연동
- 리스닝 문제 자동 생성
- 멀티 스피커 지원

<br/>

## 📊 API 문서

서버 실행 후 자동 생성된 API 문서 확인:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

<br/>

## 🤝 기여

기여는 언제나 환영합니다! 이슈를 열거나 PR을 제출해주세요.

<br/>

## 📄 라이센스

This project is licensed under the MIT License.

<br/>

## 👥 팀

**ClassMate Team** - AI 기반 교육 플랫폼 개발

---

<p align="center">
  Made with ❤️ by MateLabs Team
</p>
