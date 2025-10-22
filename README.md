# ClassMate

AI 기반 학원 관리 및 맞춤형 학습 지원 시스템

## 🚀 빠른 시작

### 환경 설정
```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env  # Neo4j, OpenAI API Key 설정 필요
```

### 시험지 파싱 (PDF → JSON)
```bash
# 문제 파싱
python3 src/teacher/parser/pipeline.py input/2026_09_mock 2026_09_mock \
  --taxonomy taxonomy.yaml --parser-mode vlm

# Neo4j 업로드 (임베딩 포함)
python3 src/teacher/parser/upload_problems.py output --init-schema
```

### API 서버 실행
```bash
# Neo4j 연결 테스트
python3 src/utils/test_neo4j.py

# 백엔드 서버 실행
PYTHONPATH=./src python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 프론트엔드 서버 실행 (새 터미널)
cd src/web
npm install
npm run dev
```

### 팀원 컴퓨터에서 접속하기 🌐

#### 1. 현재 컴퓨터 IP 주소 확인
```bash
hostname -I | awk '{print $1}'
# 예시 출력: 172.31.56.156
```

#### 2. 팀원이 브라우저에서 접속
**같은 Wi-Fi 네트워크에 연결된 팀원**은 다음 주소로 접속:
```
http://YOUR_IP:5173
```
예시: `http://172.31.56.156:5173`

#### 3. Windows 방화벽 설정 (필요시)
Windows에서 포트가 차단되어 있다면:
```powershell
# PowerShell (관리자 권한)
New-NetFirewallRule -DisplayName "ClassMate Frontend" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "ClassMate Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

#### 4. 서버 주소
- **프론트엔드**: http://YOUR_IP:5173
- **백엔드 API**: http://YOUR_IP:8000
- **API 문서**: http://YOUR_IP:8000/docs

> **참고**: vite.config.ts에서 `host: '0.0.0.0'` 설정으로 네트워크 접근이 활성화되어 있습니다.

### 신규 기능 사용하기

#### 1. 선생님 - 시험지 업로드
```bash
# 1. 선생님 로그인 (ID: T-01, PW: teacher)
# 2. "시험지 업로드" 탭 선택
# 3. 파일 드래그 앤 드롭 (또는 클릭하여 선택)
#    예시: 2026_09_mock_question.pdf, 2026_09_mock_answer.pdf
# 4. AI가 자동으로 시험 ID와 파일 유형 분류
# 5. "확인 및 업로드" 클릭
```

#### 2. 선생님 - 학생 기록 작성
```bash
# 1. 선생님 로그인 (ID: T-01, PW: teacher)
# 2. "학생 기록 작성" 탭 선택
# 3. 왼쪽 목록에서 학생 선택
# 4. 출석/숙제/특이사항/영역별 점수 입력
# 5. 각 섹션별 "저장" 버튼 클릭
```

#### 3. 학생 - AI 챗봇 상담
```bash
# 1. 학생 로그인 (ID: S-01, PW: test)
# 2. 채팅창에 질문 입력
#    예시: "나의 약점이 뭐야?", "독해 문제 내줘"
# 3. AI가 GraphRAG로 컨텍스트 검색 후 맞춤 응답
# 4. 문제 풀이 시 5지선다 옵션 클릭
```

## 📚 문서

- **[발표 자료 (PRESENTATION.md)](PRESENTATION.md)** - 프로젝트 전체 소개 (PPT용) ⭐
- **[Claude 작업 가이드](docs/CLAUDE_GUIDE.md)** - 새 세션 시작 가이드
- **[아키텍처](docs/ARCHITECTURE.md)** - 시스템 전체 구조
- **[API 문서](docs/api/API_README.md)** - REST API 사용법

## 🔌 주요 API 엔드포인트

### 인증
- `POST /api/auth/login` - 학생 로그인
- `POST /api/auth/teacher/login` - 선생님 로그인
- `POST /api/auth/parent/login` - 학부모 로그인

### 선생님 (신규 ⭐)
- `POST /api/teachers/upload` - 시험지 업로드
- `PATCH /api/teachers/student-record/{student_id}` - 학생 기록 업데이트
- `GET /api/teachers/student-detail/{student_id}` - 학생 상세 정보 조회
- `GET /api/teachers/my-students/{teacher_id}` - 담당 학생 목록

### 학생
- `POST /api/chat/student` - AI 챗봇 대화
- `GET /api/student/{student_id}/problems` - 추천 문제 조회

### 학부모
- `POST /api/chat/parent` - AI 상담 대화
- `GET /api/parent/child/{student_id}` - 자녀 학습 현황

## 💡 개발 팁

### 파일명 파싱 패턴 추가
`src/web/src/utils/fileNameParser.ts` 파일에서 패턴 수정:
```typescript
const typePatterns = {
  question: ['_문제지', '_문제', '_question', '_q'],
  answer: ['_정답지', '_정답', '_답지', '_answer', '_ans'],
  solution: ['_해설지', '_해설', '_풀이', '_solution', '_sol']
};
```

### 학생 데이터 추가/수정
`data/json/students_rag.json` 파일 편집:
```json
{
  "student_id": "S-XX",
  "name": "학생이름",
  "attendance": { "total_sessions": 0, "absent": 0, "perception": 0 },
  "homework": { "assigned": 0, "missed": 0 },
  "notes": { "attitude": "", "school_exam_level": "", "csat_level": "" },
  "assessment": {
    "radar_scores": {
      "grammar": 0, "vocabulary": 0, "reading": 0,
      "listening": 0, "writing": 0
    }
  }
}
```

### 새로운 AI Function 추가
`src/student/services/student_agent_service.py`에서 도구 정의:
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "your_new_function",
            "description": "함수 설명",
            "parameters": {...}
        }
    }
]
```

## 🏗️ 프로젝트 구조

```
ClassMate/
├── src/
│   ├── teacher/                          # 선생님 기능 (파싱, 업로드)
│   ├── student/                          # 학생 AI 에이전트
│   ├── parent/                           # 학부모 기능
│   ├── shared/                           # 공유 유틸리티
│   │   ├── prompts/                      # 프롬프트 관리
│   │   └── database/                     # DB 연결
│   ├── web/                              # React 프론트엔드
│   │   ├── src/
│   │   │   ├── pages/                    # 페이지 컴포넌트
│   │   │   │   ├── StudentDashboard.tsx
│   │   │   │   ├── ParentDashboard.tsx
│   │   │   │   └── TeacherDashboard.tsx
│   │   │   ├── components/               # 재사용 컴포넌트
│   │   │   │   ├── ExamUploadZone.tsx    # 신규 ⭐
│   │   │   │   └── StudentRecordEditor.tsx # 신규 ⭐
│   │   │   └── utils/
│   │   │       └── fileNameParser.ts     # 신규 ⭐
│   │   └── package.json
│   ├── api/                              # FastAPI 백엔드
│   │   ├── main.py                       # 메인 앱
│   │   └── routers/
│   │       ├── auth.py                   # 인증
│   │       ├── chat.py                   # 채팅
│   │       └── teachers.py               # 선생님 API (신규 ⭐)
│   └── utils/                            # 유틸리티 스크립트
├── data/
│   └── json/
│       └── students_rag.json             # 학생 데이터 (신규 ⭐)
├── input/                                # 입력 파일 (시험지 PDF)
├── output/                               # 출력 파일 (파싱 결과)
├── docs/                                 # 문서
├── PRESENTATION.md                       # 발표 자료 (신규 ⭐)
└── requirements.txt                      # Python 패키지
```

## 🎯 주요 기능

### 선생님 백오피스
- 📤 **지능형 시험지 업로드** (신규 ⭐)
  - 드래그 앤 드롭 멀티파일 업로드
  - AI 기반 파일명 파싱 (시험 ID, 파일 유형 자동 분류)
  - 시험별 자동 그룹핑 (문제지/정답지/해설지)
  - 병렬 업로드 (Promise.all)
- 📝 **학생 기록 관리** (신규 ⭐)
  - 출석/숙제/특이사항/영역별 점수 관리
  - DB 스키마 기반 설계 (students_rag.json)
  - 섹션별 탭 UI + 실시간 통계
  - RESTful API (PATCH) 연동
- 📄 시험지 자동 파싱 (VLM + OpenDataLoader)
- 👥 학생 관리 대시보드

### 학생
- 🤖 **AI 챗봇 맞춤 학습 코칭**
  - GraphRAG 기반 컨텍스트 검색
  - GPT-4.1-mini 에이전트 (Function Calling)
  - 실시간 쿼리 임베딩 (Qwen3, 1024D)
- 📊 학습 현황 대시보드
- 🎯 **개인 맞춤형 문제 추천/생성**
  - DB 1,844개 문제 중 CEFR 레벨 매칭
  - o4-mini 실시간 문제 생성
- 💬 대화 이력 관리 (ChatGPT 스타일)
- ✅ 인터랙티브 문제 풀이 (5지선다, 멀티턴 평가)

### 학부모
- 👀 자녀 학습 현황 실시간 확인
- 💬 AI 상담사 (자녀 학습 분석)
- 📈 영역별 점수 분석 (레이더 차트)

## 🛠️ 기술 스택

### Frontend
- **React** + **TypeScript** - 타입 안정성
- **Vite** - 빠른 개발 서버
- **TailwindCSS** - 유틸리티 CSS
- **Lucide React** - 아이콘

### Backend
- **FastAPI** - 고성능 Python 웹 프레임워크
- **Pydantic** - 데이터 검증
- **Uvicorn** - ASGI 서버

### Database
- **Neo4j** - Graph Database + Vector Search
- **JSON** - 학생 데이터 저장 (students_rag.json)

### AI/ML
- **GPT-4.1-mini** - AI Agent 오케스트레이션 (2025-04-14)
  - Function Calling 정확도 ↑
  - 레이턴시 50% ↓
  - 비용 83% ↓
- **o4-mini** - 문제 생성 (추론 특화)
- **Qwen3-Embedding-0.6B** - 쿼리 임베딩 (1024D, 오프라인 가능)
- **GPT-4o** - Fallback 모델

### Document Processing
- **Google Document AI** - PDF 파싱
- **OpenDataLoader** - 문서 구조 분석

## 📞 지원

문제가 발생하면 [Issues](https://github.com/your-org/ClassMate/issues)에 보고해주세요.
