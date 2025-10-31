# ClassMate 프로젝트 코드 구조 문서

## 📋 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [전체 디렉토리 구조](#전체-디렉토리-구조)
3. [주요 모듈 상세 설명](#주요-모듈-상세-설명)
4. [AI 에이전트 시스템 (Function Calling + ReAct)](#ai-에이전트-시스템-function-calling--react)
5. [데이터베이스 및 RAG](#데이터베이스-및-rag)
6. [API 서버](#api-서버)
7. [프론트엔드](#프론트엔드)

---

## 프로젝트 개요

**ClassMate**는 영어 학원을 위한 AI 기반 맞춤형 학습 관리 플랫폼입니다.

### 핵심 기술 스택
- **Backend**: FastAPI + Neo4j (GraphDB + Vector Search)
- **Frontend**: React 19.1 + TypeScript 5.9 + Vite 7.1
- **AI**: OpenAI GPT-4.1-mini, o4-mini (Reasoning), o3 (Advanced Reasoning)
- **RAG**: GraphRAG (Neo4j Vector Search + Graph Traversal)
- **TTS**: OpenAI TTS-1 (고품질 음성 생성, 다화자 지원)
- **Architecture**: Function Calling + ReAct (Reasoning + Acting)

### 🔒 보안 및 기밀 정책
- **모델 정보 비공개**: 모든 챗봇이 사용 모델(GPT, OpenAI, Claude 등) 정보를 절대 공개하지 않음
- **역할별 정체성 강화**:
  - 학생 챗봇: "친구", "학습 메이트" (AI 아님)
  - 학부모 챗봇: "ClassMate 전문 상담사"
  - 교사 챗봇: "ClassMate 교육 보조 시스템"

---

## 전체 디렉토리 구조

```
src/
├── api/                    # FastAPI 백엔드 API 서버
│   ├── main.py            # FastAPI 앱 진입점
│   ├── models/            # Pydantic 데이터 모델
│   ├── routers/           # API 엔드포인트 라우터
│   └── services/          # 비즈니스 로직 서비스
│
├── student/               # 학생 모듈
│   ├── routers/          # 학생 채팅 라우터
│   ├── services/         # 학생 AI 에이전트 서비스
│   └── tests/            # 학생 모듈 테스트
│
├── parent/               # 학부모 모듈
│   ├── routers/         # 학부모 채팅 라우터
│   └── services/        # 학부모 AI 에이전트 서비스
│
├── teacher/             # 교사 모듈
│   ├── routers/        # 교사 채팅 라우터
│   ├── services/       # 교사 AI 에이전트 서비스
│   ├── daily/          # 일일 학생 기록 처리
│   └── parser/         # 시험지 파싱 파이프라인
│
├── shared/             # 공유 모듈
│   ├── prompts/       # 프롬프트 관리 시스템
│   └── services/      # 공유 서비스 (GraphRAG, TTS, 외부 API 등)
│
├── web/               # React 프론트엔드
│   └── src/
│       ├── pages/    # 페이지 컴포넌트
│       ├── components/ # 재사용 컴포넌트
│       └── api/      # API 클라이언트
│
└── utils/            # 유틸리티 스크립트
```

---

## 주요 모듈 상세 설명

### 1. API 서버 (`src/api/`)

#### `main.py` - FastAPI 애플리케이션 진입점
```python
기능:
- FastAPI 앱 초기화 및 설정
- CORS 미들웨어 설정 (React 개발 서버 연동)
- Neo4j 연결 관리 (lifespan context)
- Static 파일 서빙 (TTS 오디오 파일)
- 라우터 등록 (auth, chat, dashboard, students 등)
- Health check 엔드포인트 (/health)
```

#### `services/neo4j_service.py` - Neo4j 데이터베이스 서비스
```python
기능:
- Singleton 패턴으로 Neo4j 연결 관리
- 학생 CRUD (생성, 조회, 수정, 삭제)
- 문제 CRUD 및 필터링 (영역, 난이도, CEFR 레벨)
- Daily Input 생성 및 조회 (학생 일일 기록)
- 통계 조회 (문제/학생 분포)
- 벡터 검색 (임베딩 기반 유사도 검색)

주요 메서드:
- get_students(): 학생 목록 조회 (페이징, 필터링)
- get_student_by_id(): 학생 상세 정보 조회
- get_problems(): 문제 목록 조회
- search_problems_by_text(): 벡터 검색으로 문제 찾기
- create_daily_input(): 학생 일일 기록 생성
```

#### `routers/` - API 엔드포인트 라우터

| 파일 | 기능 |
|------|------|
| `auth.py` | 로그인, 로그아웃, 세션 관리 |
| `chat.py` | AI 채팅 엔드포인트 (학생/학부모/교사 통합) |
| `dashboard.py` | 대시보드 데이터 (성적, 출석, 통계) |
| `students.py` | 학생 CRUD 및 검색 |
| `problems.py` | 문제 CRUD 및 검색 |
| `teachers.py` | 교사 관련 API |
| `parents.py` | 학부모 관련 API |
| `classes.py` | 반 정보 관리 |
| `audio.py` | TTS 오디오 파일 제공 |

---

### 2. 학생 모듈 (`src/student/`)

#### `services/agent_service.py` - 학생 AI 에이전트 (⭐ 핵심)
```python
클래스: StudentAgentService

핵심 기능:
1. Function Calling 기반 AI 에이전트
2. ReAct (Reasoning + Acting) 모드 지원
3. 지능형 라우팅 (gpt-4.1-mini vs o4-mini)
4. 문제 생성 (듣기, 독해, 문법, 어휘, 쓰기)
5. 쓰기 평가 (AI 기반 종합 평가)
6. 학생 정보 조회 (GraphRAG)
7. 🤖 정체성 관리: "친구", "학습 메이트" (AI 언급 금지)

주요 메서드:
- chat(): 학생과 대화 (Function Calling)
- _react_chat(): ReAct 모드 (복잡한 다단계 작업)
- _route_query(): 쿼리 복잡도 분석 및 모델 선택
- _needs_react(): ReAct 모드 필요 여부 판단
- _generate_problem(): AI 문제 생성 (o4-mini)
- _evaluate_writing(): 쓰기 답안 평가 (o4-mini)
- _recommend_problems(): DB에서 문제 추천
- _postprocess_listening_problem(): 듣기 문제 후처리 (음성 생성, 한글 제거)

Function Calling 도구 (총 8개):
1. get_student_context: 학생 정보 조회
2. recommend_problems: DB 문제 추천
3. generate_problem: AI 문제 생성 (고품질)
4. evaluate_writing: 쓰기 평가
5. lookup_word: 영어 단어 검색
6. fetch_news: 영어 뉴스 검색
7. analyze_text_difficulty: 텍스트 난이도 분석
8. check_grammar: 문법 검사

🔒 모델 정보 비공개:
- 학생이 "너 GPT야?", "어떤 AI야?" 질문 시 절대 공개하지 않음
- 대신 "나는 너의 영어 공부를 도와주는 친구야!" 같은 응답 제공
```

#### `routers/chat.py` - 학생 채팅 API
```python
기능:
- POST /api/student/chat: 학생 채팅 엔드포인트
- 멀티턴 대화 지원 (chat_history)
- 세션 관리 (session_id)
```

---

### 3. 학부모 모듈 (`src/parent/`)

#### `services/agent_service.py` - 학부모 AI 에이전트
```python
클래스: ParentAgentService

핵심 기능:
1. 학부모 맞춤 Function Calling 에이전트
2. ReAct 모드 지원 (복잡한 분석)
3. 자녀 학습 현황 분석
4. 학습 조언 및 개선 계획 제공
5. 🤖 정체성: "ClassMate 학원 전문 상담사"

주요 메서드:
- chat(): 학부모와 대화
- _react_chat(): ReAct 모드
- _get_child_info(): 자녀 정보 조회
- _analyze_performance(): 성적 분석
- _get_study_advice(): 맞춤형 학습 조언 (GPT-4o)
- _recommend_improvement_areas(): 개선 영역 추천
- _generate_problem(): 가정 학습용 문제 생성 (듣기 문제 포함)
- _add_parent_guidance(): 듣기 문제에 학부모 지도 가이드 추가

Function Calling 도구 (총 10개):
1. get_child_info: 자녀 상세 정보
2. analyze_performance: 성적 분석
3. get_study_advice: 학습 조언
4. get_attendance_status: 출석 현황
5. recommend_improvement_areas: 개선 계획
6. generate_problem: 문제 생성 (가정 학습용, OpenAI TTS 통합)
7. lookup_word: 단어 검색
8. fetch_news: 뉴스 검색
9. analyze_text_difficulty: 난이도 분석
10. check_grammar: 문법 검사

🔒 모델 정보 비공개:
- 학부모가 기술 질문 시 "자체 개발 시스템" 등으로 응답
- 절대 GPT, OpenAI, o4-mini 등 모델명 공개하지 않음
```

---

### 4. 교사 모듈 (`src/teacher/`)

#### `services/teacher_agent_service.py` - 교사 AI 에이전트
```python
클래스: TeacherAgentService

핵심 기능:
1. 반 관리 및 학생 모니터링
2. 성적/태도 기준 학생 검색
3. UI 트리거 (시험지 업로드, Daily Input)
4. 🤖 정체성: "ClassMate 교육 보조 시스템"

주요 메서드:
- chat(): 교사와 대화
- _react_chat(): ReAct 모드
- _get_my_class_students(): 담당 학생 조회
- _search_students_by_score(): 점수 기준 검색
- _search_students_by_behavior(): 태도 기준 검색
- _trigger_exam_upload_ui(): 시험지 업로드 UI 열기
- _trigger_daily_input_ui(): Daily Input UI 열기

Function Calling 도구 (총 10개):
1. get_my_class_students: 내 반 학생 목록
2. search_students_by_score: 점수 기준 검색
3. search_students_by_behavior: 태도 기준 검색
4. trigger_exam_upload_ui: UI 트리거 (시험지)
5. trigger_daily_input_ui: UI 트리거 (기록부)
6. get_student_details: 학생 상세 정보
7. lookup_word: 단어 검색
8. fetch_news: 뉴스 검색
9. analyze_text_difficulty: 난이도 분석
10. check_grammar: 문법 검사

🔒 모델 정보 비공개:
- 교사가 기술 질문 시 프로페셔널하게 회피
```

#### `parser/` - 시험지 파싱 파이프라인
```python
주요 파일:
- master_pipeline.py: 통합 파이프라인 (Chandra HTML → Markdown)
- chandra_pipeline.py: HTML 파싱 및 문제 추출
- solution_parser.py: 정답/해설 파싱
- rationale_processor.py: 해설(Rationale) 추출
- docai_utils.py: Google Document AI 연동 (PDF OCR)
- llm_mapper.py: LLM 기반 메타데이터 매핑
- upload_problems.py: Neo4j 업로드

파이프라인 흐름:
1. Chandra HTML → Beautiful Soup 파싱
2. 문제 추출 (p, a, b, c, d, e 태그)
3. 이미지/표 추출 및 캡셔닝
4. 정답/해설 매칭
5. LLM 메타데이터 매핑 (CEFR, 영역, 난이도)
6. Neo4j 업로드 (임베딩 포함)
```

#### `daily/` - 일일 학생 기록 처리
```python
- student_processor.py: 학생 데이터 처리
- upload_students.py: 학생 정보 Neo4j 업로드
```

---

### 5. 공유 모듈 (`src/shared/`)

#### `prompts/prompt_manager.py` - 프롬프트 관리 시스템 (⭐ 핵심)
```python
클래스: PromptManager

기능:
- 역할별(student, parent, teacher) 프롬프트 관리
- 모델별(gpt-4.1-mini, o4-mini, o3) 최적화
- 문제 생성 프롬프트 템플릿
- 🔒 모델 정보 비공개 정책 프롬프트 포함

주요 메서드:
- get_system_prompt(role, model, context): 시스템 프롬프트 생성
- get_problem_generation_prompt(area, difficulty, topic): 문제 생성 프롬프트

프롬프트 구성:
1. 역할별 Identity (정체성)
   - student_agent: "friendly learning companion (학습 메이트)"
   - parent: "ClassMate 학원 전문 상담사"
   - teacher_agent: "ClassMate teaching assistant"
2. Tone & Guidelines (말투 및 가이드라인)
3. Function Calling 규칙
4. 응답 포맷팅 규칙 (이모지, 섹션, 불릿 포인트)
5. 문제 생성 상세 규칙 (듣기 문제 특수 처리)
6. 🔒 모델 정보 비공개 규칙 (절대 GPT, OpenAI 등 언급 금지)
```

#### `services/graph_rag_service.py` - GraphRAG 서비스 (⭐ 핵심)
```python
클래스: GraphRAGService

기능:
1. 벡터 검색 (Vector Search)
   - Qwen3-Embedding-0.6B 모델 사용
   - Cosine Similarity 기반 유사도 검색

2. 그래프 탐색 (Graph Traversal)
   - 학생 → 성적/출석/숙제/반/선생님 관계 탐색
   - 동료 학생 비교 (또래 분석)

3. RAG 컨텍스트 생성
   - 벡터 검색 + 그래프 탐색 결합
   - 자연어 컨텍스트로 변환

주요 메서드:
- get_embedding(text): 텍스트 임베딩 생성 (1024 dims)
- vector_search_students(query): 벡터 유사도 검색
- get_student_graph_context(student_id): 그래프 탐색
- get_rag_context(student_id, query): RAG 컨텍스트 생성
- search_problems_for_student(student_id): 맞춤 문제 추천
```

#### `services/tts_service.py` - TTS 음성 생성 서비스 (⭐ 핵심)
```python
클래스: TTSService

기능:
- OpenAI TTS-1 API 연동
- 듣기 문제 고품질 음성 생성 (네이티브급)
- 다화자 대화 지원 (2-4명, 각기 다른 목소리)
- 화자별 목소리 할당:
  - 여성: Samantha, Karen, Victoria
  - 남성: David, Daniel, Mark
- [SPEAKERS] JSON 파싱 및 화자 정보 자동 생성
- 음성 파일 캐싱 (세션별)
- 효과음 믹싱 (전화벨, 카페 소음 등)
- 한글 텍스트 자동 제거 (TTS 음성에서 제외)
  - 괄호 안의 한글 번역만 제거
  - 완전히 한글로만 된 설명 줄만 제거
  - 영어 대화 스크립트는 유지

주요 메서드:
- create_listening_audio(content, speed, session_id): 전체 오디오 생성
- get_or_create_audio(content, force_regenerate, session_id): 캐싱 지원
- parse_listening_problem(content): [SPEAKERS], [AUDIO] 파싱
- parse_dialogue_lines(audio_text): 대화 스크립트 분리
- get_openai_voice(speaker_name, speakers): 화자별 음성 매핑
- generate_tts_segment(text, voice, speed): 개별 음성 생성
```

#### `services/external_api_service.py` - 외부 API 서비스
```python
제공 서비스:
1. DictionaryService: Free Dictionary API (단어 검색)
2. NewsService: NewsAPI (영어 뉴스)
3. TextAnalysisService: textstat (CEFR 레벨 분석)
4. GrammarCheckService: LanguageTool (문법 검사)
```

---

### 6. 프론트엔드 (`src/web/`)

#### 주요 페이지 컴포넌트

| 파일 | 기능 |
|------|------|
| `Landing.tsx` | 랜딩 페이지 (로그인 이전) |
| `UnifiedLogin.tsx` | 통합 로그인 (학생/학부모/교사) |
| `StudentDashboard.tsx` | 학생 대시보드 (AI 채팅, 성적, 엔터 후 커서 유지) |
| `ParentDashboard.tsx` | 학부모 대시보드 (자녀 모니터링, 중지 버튼, 엔터 후 커서 유지) |
| `TeacherDashboard.tsx` | 교사 대시보드 (반 관리, 시험지 업로드) |

#### 핵심 컴포넌트
- AI 채팅 인터페이스 (멀티턴 대화, Quick Reply 버튼)
- TTS 음성 재생 (듣기 문제, 다화자 지원)
- 시험지 업로드 (Drag & Drop)
- 학생 기록부 작성 (Daily Input)
- **채팅 입력 개선**:
  - 엔터 키 후 커서 자동 유지 (chatInputRef)
  - 중지 버튼 (생성 중 중단 가능)

#### UI/UX 개선사항
- **웹 타이틀**: "ClassMate"
- **파비콘**: ClassMate 다람쥐 로고
- **채팅 UX**:
  - 엔터 후 입력창 포커스 유지
  - 로딩 중 중지 버튼 표시
  - Shift+Enter로 줄바꿈

---

## AI 에이전트 시스템 (Function Calling + ReAct)

### 1. Function Calling 아키텍처

#### 📍 위치
```
src/student/services/agent_service.py    (학생 에이전트)
src/parent/services/agent_service.py     (학부모 에이전트)
src/teacher/services/teacher_agent_service.py (교사 에이전트)
```

#### 동작 원리

```
1. 사용자 메시지 입력
   ↓
2. _route_query() - 쿼리 복잡도 분석
   ↓
3. 모델 선택 (gpt-4.1-mini vs o4-mini)
   ↓
4. OpenAI Chat Completion 호출 (tools 파라미터)
   ↓
5. LLM이 함수 호출 결정
   ↓
6. _execute_function() - 함수 실행
   ↓
7. 듣기 문제의 경우 직접 반환 ([AUDIO]/[SPEAKERS] 태그 보존)
   ↓
8. 함수 결과를 메시지에 추가
   ↓
9. 최종 응답 생성
```

#### 예시: 학생이 "문법 문제 내줘" 입력

```python
# Step 1: 사용자 메시지
message = "문법 문제 내줘"

# Step 2: Routing (간단한 요청 → gpt-4.1-mini)
routing_decision = self._route_query(message, student_id)
# → "intelligence"

# Step 3: LLM 호출 (Function Calling)
response = self.client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ],
    tools=self.functions,
    tool_choice="auto"
)

# Step 4: LLM이 generate_problem 함수 호출 결정

# Step 5: 함수 실행
function_response = self._generate_problem(
    student_id="S-01",
    area="문법"
)
# → o4-mini가 문법 문제 생성

# Step 6: 듣기 문제가 아니므로 일반 처리
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": function_response
})

# Step 7: 최종 응답 생성
final_response = self.client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=messages
)
# → "문법 문제 준비했어! [문제 내용]"
```

#### 듣기 문제 특수 처리

```python
# 듣기 문제의 경우: [AUDIO]와 [SPEAKERS] 태그를 보존하기 위해 직접 반환
if function_name == "generate_problem" and arguments.get("area", "").lower() in ['듣기', 'listening', 'ls']:
    if '[AUDIO]' in function_response or '[SPEAKERS]' in function_response:
        print("🎧 듣기 문제: [AUDIO]/[SPEAKERS] 태그 보존을 위해 직접 반환")
        return {
            "message": function_response,
            "model_info": {...}
        }
```

---

### 2. ReAct (Reasoning + Acting) 아키텍처

#### 📍 위치
```python
# 각 agent_service.py 파일 내:
def _needs_react(message: str) -> bool:
    """ReAct 모드 필요 여부 판단"""
    ...

def _react_chat(student_id, message, chat_history, max_steps=5):
    """ReAct 모드 실행"""
    ...
```

#### 동작 원리

ReAct는 **복잡한 다단계 작업**을 처리하기 위한 패턴입니다.

```
Thought (생각) → Action (함수 호출) → Observation (결과) → Thought → ...
```

#### ReAct 모드 진입 조건

```python
def _needs_react(self, message: str) -> bool:
    # 패턴 1: 연결어 ("하고", "찾아서")
    if "하고" in message and "해줘" in message:
        return True

    # 패턴 2: "먼저...그다음"
    if "먼저" in message and "그다음" in message:
        return True

    # 패턴 3: 동사 3개 이상
    action_verbs = ['찾', '분석', '추천', '확인', '조회']
    if count_verbs(message) >= 3:
        return True

    return False
```

#### 예시: 학부모가 "민준이 약점 찾아서 4주 학습 계획 세워줘" 입력

```python
# ReAct 모드 활성화
if self._needs_react(message):
    return self._react_chat(student_id, message, chat_history)

# ReAct 루프
for step in range(1, max_steps + 1):
    print(f"--- ReAct Step {step}/5 ---")

    # LLM 호출 (o4-mini - 추론 모델)
    response = self.client.chat.completions.create(
        model="o4-mini",
        messages=messages,
        tools=self.functions,
        tool_choice="auto"
    )

    # Thought (LLM의 생각 과정)
    if assistant_message.content:
        print(f"💭 Thought: {assistant_message.content}")

    # Action (함수 호출)
    if assistant_message.tool_calls:
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            print(f"🔧 Action: {function_name}(...)")

            # 함수 실행
            result = self._execute_function(function_name, arguments)

            # Observation (결과 관찰)
            print(f"📊 Observation: {result[:200]}...")

            # 메시지에 추가 (다음 Thought에 사용)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
    else:
        # Final Answer (최종 답변)
        print("✅ Final Answer Reached")
        return assistant_message.content
```

---

### 3. 모델 라우팅 전략

#### Intelligent Routing (지능형 라우팅)

| 질문 유형 | 모델 | 이유 |
|-----------|------|------|
| "문제 내줘" | gpt-4.1-mini | 간단한 함수 호출 |
| "안녕?" | gpt-4.1-mini | 인사말 |
| "점수 알려줘" | gpt-4.1-mini | DB 조회 |
| "왜 이 답이 틀렸어?" | o4-mini | 심화 설명 필요 |
| "가정법 과거완료를 자세히 설명해줘" | o4-mini | 복잡한 개념 |
| "독해 실력을 늘리려면?" | o4-mini | 전략 분석 |

#### Quality Check & Fallback

```python
# o4-mini 응답 품질이 낮으면 o3로 재시도
if primary_model == "o4-mini" and not self._check_response_quality(response_content):
    print("⚠️  o4-mini response quality low, falling back to o3...")
    final_response_o3 = self.client.chat.completions.create(
        model="o3",  # Advanced reasoning
        messages=messages
    )
    response_content = final_response_o3.choices[0].message.content
```

---

## 데이터베이스 및 RAG

### Neo4j GraphDB 스키마

```cypher
// 노드 타입
(:Student)        - 학생
(:Problem)        - 문제
(:Class)          - 반
(:Teacher)        - 선생님
(:Assessment)     - 평가/성적
(:Attendance)     - 출석
(:Homework)       - 숙제
(:RadarScores)    - 영역별 점수
(:DailyInput)     - 일일 기록

// 관계
(:Student)-[:ENROLLED_IN]->(:Class)
(:Student)-[:HAS_ASSESSMENT]->(:Assessment)
(:Student)-[:HAS_ATTENDANCE]->(:Attendance)
(:Student)-[:HAS_HOMEWORK]->(:Homework)
(:Student)-[:HAS_RADAR]->(:RadarScores)
(:Student)-[:HAS_INPUT]->(:DailyInput)
(:Teacher)-[:TEACHES]->(:Class)
(:Problem)-[:HAS_TABLE]->(:Tbl)
(:Problem)-[:HAS_FIG]->(:Fig)
```

### GraphRAG 파이프라인

```
1. 사용자 질문: "민준이 약점이 뭐야?"
   ↓
2. 쿼리 임베딩 생성 (Qwen3-Embedding-0.6B)
   ↓
3. Vector Search (Cosine Similarity > 0.7)
   ↓
4. Graph Traversal (Student → Assessment → RadarScores)
   ↓
5. 컨텍스트 조합 (Vector + Graph)
   ↓
6. LLM에게 컨텍스트 제공
   ↓
7. 자연어 답변 생성
```

---

## API 서버

### 주요 엔드포인트

```
POST /api/auth/login          # 로그인
POST /api/auth/logout         # 로그아웃
GET  /api/auth/me             # 현재 사용자

POST /api/chat/student        # 학생 채팅
POST /api/chat/parent         # 학부모 채팅
POST /api/chat/teacher        # 교사 채팅

GET  /api/students            # 학생 목록
GET  /api/students/{id}       # 학생 상세
GET  /api/problems            # 문제 목록
GET  /api/problems/{id}       # 문제 상세

GET  /api/dashboard/student/{id}  # 학생 대시보드 데이터
GET  /api/dashboard/parent/{id}   # 학부모 대시보드 데이터
GET  /api/dashboard/teacher/{id}  # 교사 대시보드 데이터

GET  /api/audio/{session_id}      # TTS 오디오 파일
```

---

## 프론트엔드

### React 19.1 + TypeScript 5.9 + Vite 7.1

```
주요 라이브러리:
- @tanstack/react-query: API 상태 관리
- React Router: 페이지 라우팅
- Tailwind CSS: 스타일링
- Lucide React: 아이콘
```

### 주요 기능

1. **통합 로그인**
   - 학생/학부모/교사 역할 선택
   - 세션 관리 (localStorage)

2. **AI 채팅 인터페이스**
   - 멀티턴 대화 (chat_history)
   - Quick Reply 버튼 (문제 유형 선택)
   - 마크다운 렌더링
   - TTS 음성 재생 (듣기 문제, 다화자)
   - 엔터 후 커서 자동 유지 (chatInputRef)
   - 중지 버튼 (생성 중 중단 가능)

3. **대시보드**
   - 성적 차트 (Radar Chart)
   - 출석률, 숙제 완료율
   - 영역별 점수 시각화

4. **교사 기능**
   - 시험지 업로드 (Drag & Drop)
   - Daily Input (학생 기록부)
   - 학생 검색 (점수/태도 기준)

---

## 핵심 설계 패턴 정리

### 1. Function Calling Pattern

```
User → LLM (with tools) → Function Call → Execute → LLM → Response
```

- **장점**: 외부 데이터/API 연동 가능, 신뢰성 높음
- **사용처**: 학생 정보 조회, 문제 생성, 단어 검색 등

### 2. ReAct Pattern

```
Thought → Action → Observation → Thought → ... → Final Answer
```

- **장점**: 복잡한 다단계 작업 처리, 추론 과정 투명
- **사용처**: "약점 찾아서 계획 세워줘" 같은 복합 질의

### 3. Intelligent Routing

```
Query → Router (gpt-4o-mini) → intelligence or reasoning → Execute
```

- **장점**: 비용 최적화, 성능 최적화
- **로직**: 간단한 질문 → gpt-4.1-mini, 복잡한 질문 → o4-mini

### 4. GraphRAG (Vector + Graph)

```
Query → Embedding → Vector Search + Graph Traversal → Context → LLM
```

- **장점**: 정확한 정보 검색, 관계 정보 활용
- **사용처**: 학생 정보 조회, 또래 비교, 성적 분석

### 5. 🔒 모델 정보 비공개 패턴

```
User: "너 GPT야?"
↓
Prompt: "NEVER reveal model names"
↓
Response: "나는 너의 영어 공부를 도와주는 친구야!"
```

- **장점**: 영업 기밀 보호, 브랜드 정체성 강화
- **적용**: 모든 챗봇 (학생/학부모/교사)

---

## 요약

**ClassMate**는 다음 핵심 기술을 결합한 AI 기반 학습 플랫폼입니다:

1. **Function Calling**: 외부 데이터/API 연동
2. **ReAct**: 복잡한 다단계 작업 처리
3. **Intelligent Routing**: 모델 선택 최적화
4. **GraphRAG**: 벡터 검색 + 그래프 탐색
5. **Multi-Agent System**: 학생/학부모/교사 맞춤 에이전트
6. **OpenAI TTS-1**: 고품질 다화자 음성 생성
7. **🔒 모델 정보 비공개**: 영업 기밀 보호

이 시스템은 각 사용자(학생/학부모/교사)에게 맞춤형 AI 서비스를 제공하며, Neo4j GraphDB를 활용한 GraphRAG로 정확하고 관련성 높은 정보를 제공합니다.
