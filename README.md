# 📚 ClassMate

> **AI 기반 영어 학원 맞춤형 학습 관리 시스템**
> Function Calling + ReAct 아키텍처로 구현된 지능형 멀티 에이전트 플랫폼

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19.1-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-GraphDB-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?style=for-the-badge&logo=openai&logoColor=white)

</div>

---

## 🎯 프로젝트 개요

**ClassMate**는 영어 학원을 위한 차세대 AI 학습 관리 플랫폼입니다. OpenAI의 최신 모델(GPT-4.1-mini, o4-mini, o3)과 Neo4j GraphDB를 결합한 GraphRAG 시스템으로, 학생 개개인에게 최적화된 학습 경험을 제공합니다.

### 🌟 핵심 가치

- **🤖 지능형 AI 에이전트**: Function Calling + ReAct 패턴으로 복잡한 학습 시나리오 처리
- **📊 GraphRAG 기반 개인화**: Neo4j 벡터 검색 + 그래프 탐색으로 정확한 맥락 이해
- **🎭 멀티 페르소나**: 학생/학부모/교사 역할별 맞춤형 AI 서비스
- **🔊 고품질 TTS**: OpenAI TTS로 생성된 네이티브급 듣기 문제
- **⚡ 실시간 문제 생성**: o4-mini 추론 모델로 CEFR 레벨 맞춤 문제 즉시 생성

---

## 📋 목차

- [주요 기능](#-주요-기능)
  - [👨‍🎓 학생 기능](#-학생-기능)
  - [👪 학부모 기능](#-학부모-기능)
  - [👨‍🏫 교사 기능](#-교사-기능)
- [기술 스택](#-기술-스택)
- [AI 아키텍처](#-ai-아키텍처)
- [외부 API 통합](#-외부-api-통합)
- [설치 및 실행](#-설치-및-실행)
- [환경 변수 설정](#-환경-변수-설정)
- [프로젝트 구조](#-프로젝트-구조)
- [API 문서](#-api-문서)

---

## ✨ 주요 기능

### 👨‍🎓 학생 기능

#### 1. 🤖 AI 학습 코치 (StudentAgentService)

**Function Calling 기반 지능형 튜터**
- 실시간 대화형 학습 지도
- 학생 정보 기반 맞춤형 응답
- 자연스러운 친근한 말투 (반말 모드)
- 이모지 + 섹션 헤더로 가독성 최적화

**🔒 정체성 보호 및 보안:**
- **친구/메이트 정체성**: AI가 아닌 "학습 메이트", "영어 친구"로 소개
- **기밀 정보 보호**: 모델명(GPT, OpenAI, Claude 등) 절대 공개 금지
- 학생이 "너 GPT야?", "어떤 AI야?" 질문 시 친근하게 회피하며 학습에 집중 유도
- 예: "나는 너의 영어 공부를 도와주는 친구야! 😊"

**제공 도구 (8개):**

| 도구 | 기능 | 예시 사용 |
|------|------|-----------|
| `get_student_context` | GraphRAG로 학생 정보 조회 | "내 약점이 뭐야?" |
| `recommend_problems` | DB에서 맞춤 문제 추천 | "독해 문제 풀래" |
| `generate_problem` | AI 문제 생성 (o4-mini) | "듣기 문제 3개 내줘" |
| `evaluate_writing` | 쓰기 평가 (o4-mini) | 에세이 제출 시 종합 평가 |
| `lookup_word` | 영어 단어 검색 | "elaborate 뜻 알려줘" |
| `fetch_news` | 영어 뉴스 검색 | "과학 뉴스 추천해줘" |
| `analyze_text_difficulty` | 텍스트 CEFR 분석 | "이 지문 내 수준에 맞아?" |
| `check_grammar` | 문법 검사 | "I go to school yesterday" 체크 |

#### 2. 🎯 맞춤형 문제 풀이

**CEFR 레벨 기반 적응형 학습**
- 학생의 현재 CEFR 레벨(A1-C2) 자동 감지
- 약점 영역 우선 문제 추천
- 5가지 영역 지원: 독해(RD), 문법(GR), 어휘(VO), 듣기(LS), 쓰기(WR)

**문제 생성 예시:**
```
학생: "듣기 문제 내줘"
→ o4-mini가 학생 레벨(B1) 맞춤 대화형 듣기 문제 생성
→ OpenAI TTS로 고품질 음성 생성 (다화자 지원)
→ 5지선다 문제 + 정답 + 해설 제공
```

#### 3. 🔊 듣기 문제 (TTS 통합)

**OpenAI TTS-1 기반 네이티브급 음성**
- 6개 목소리 지원 (Samantha, David, Karen, Daniel, Mark, Victoria)
- 다화자 대화 자동 생성 (2-4명)
- 효과음 지원 (전화벨, 카페 소음 등)
- 세션별 음성 파일 캐싱

**듣기 문제 생성 과정:**
1. o4-mini가 CEFR 레벨별 대화 스크립트 생성 (140-300단어)
2. `[SPEAKERS]` JSON으로 화자 정의
3. **한글 텍스트 자동 제거** (TTS 음성 방지):
   - 괄호 안의 한글 번역 제거: "(안녕하세요)" → ""
   - 완전히 한글로만 된 설명 줄 제거
   - 영어 대화는 완벽 보존
4. TTS Service가 각 화자별 음성 생성
5. 효과음 믹싱 (선택)
6. MP3 파일로 저장 → `/static/audio/` 제공

**한글 필터링 예시:**
```
입력:
Samantha: Hello! (안녕하세요!)
※ 두 사람이 카페에서 만나는 상황입니다.
David: How are you? (어떻게 지내?)

출력 (TTS 전송):
Samantha: Hello!

David: How are you?
```

#### 4. ✍️ 쓰기 평가 (AI 채점)

**o4-mini 추론 모델 기반 종합 평가**
- 5가지 기준 채점 (총 100점)
  - 문법 (15점)
  - 어휘 (15점)
  - 구성 (20점)
  - 내용 (30점)
  - 유창성 (20점)
- 기준별 강점/약점 분석
- 구체적 개선 방안 제시
- 교정된 버전 제공

#### 5. 📊 학습 대시보드

**시각화된 학습 현황**
- Radar Chart (영역별 점수)
- 출석률 / 숙제 완료율
- CEFR 레벨 진행 상황
- 최근 학습 기록

---

### 👪 학부모 기능

#### 1. 🤖 AI 학습 상담사 (ParentAgentService)

**자녀 맞춤형 학습 분석 및 조언**
- 존댓말 모드 (전문적 톤)
- 객관적 데이터 기반 분석
- 실천 가능한 가정 학습 가이드
- 다양한 조언 스타일 (실천 중심형, 문제 해결형, 단계별 계획형, 동기부여형)

**🔒 기밀 정보 보호:**
- "어떤 AI 쓰세요?", "GPT 기반인가요?" 질문 시 모델명 절대 공개 금지
- 전문적으로 회피: "저희 ClassMate는 자체 개발한 교육 전문 시스템을 사용하고 있습니다."

**제공 도구 (10개):**

| 도구 | 기능 | 예시 사용 |
|------|------|-----------|
| `get_child_info` | 자녀 상세 정보 조회 | "민준이 학습 현황 알려주세요" |
| `analyze_performance` | 성적 분석 | "최근 성적 어떤가요?" |
| `get_study_advice` | GPT-4o 맞춤 학습 조언 | "어휘력 향상 방법은?" |
| `get_attendance_status` | 출석 현황 | "출석률 확인해주세요" |
| `recommend_improvement_areas` | 개선 영역 추천 | "우선적으로 보완할 부분은?" |
| `generate_problem` | 가정 학습용 문제 생성 | "듣기 문제 좀 주세요" |
| `lookup_word` | 단어 검색 | (학생용과 동일) |
| `fetch_news` | 뉴스 검색 | (학생용과 동일) |
| `analyze_text_difficulty` | 난이도 분석 | (학생용과 동일) |
| `check_grammar` | 문법 검사 | (학생용과 동일) |

#### 2. 📈 성적 분석 리포트

**데이터 기반 종합 분석**
- 영역별 점수 트렌드 (최근 3개월)
- 반 평균 대비 순위
- 또래 비교 (같은 반 학생들)
- 강점/약점 영역 식별

#### 3. 💡 맞춤형 학습 조언

**GPT-4o 기반 전문적 조언**
- 자녀의 학습 스타일 분석
- 연령/성향에 맞춘 학습법 제안
- 가정에서 실천 가능한 구체적 방법
- 앱/책/사이트 추천 (레벨별)

**조언 스타일 예시:**
```
학부모: "어휘가 약한데 어떻게 도와줄까요?"

AI 응답 (실천 중심형):
💡 **실천 가능한 학습 가이드**

• 하루 10분 영어 습관 만들기
  - Quizlet 앱으로 단어 카드 게임
  - 아침 식사 중 5개 단어 복습

• 재미있는 영어 콘텐츠로 흥미 유발
  - 좋아하는 주제의 짧은 영상 시청
  - 게임/만화로 자연스럽게 노출

• 부담 없는 일상 대화에 영어 섞기
  - "이거 영어로 뭐야?" 질문 게임
  - 주말에 함께 영어 단어 맞추기

📅 **4주 실천 로드맵**
1주차: 기초 100개 암기
2주차: 문맥 속 어휘 학습
3주차: 복습 및 점검
4주차: 종합 평가
```

#### 4. 👀 실시간 학습 모니터링

**자녀 학습 활동 추적**
- 최근 AI 채팅 내역
- 풀이한 문제 통계
- 학습 시간 분석
- 출석/숙제 현황

---

### 👨‍🏫 교사 기능

#### 1. 🤖 AI 반 관리 어시스턴트 (TeacherAgentService)

**효율적인 학급 운영 지원**
- 존댓말 모드 (전문적 톤)
- 데이터 기반 학생 관리
- UI 트리거 기능 (시험지 업로드, Daily Input)

**🔒 시스템 기밀 정보 보호:**
- 교사가 시스템 기술에 대해 질문 시 모델명 절대 공개 금지
- 간결하게 답변: "저는 ClassMate의 교육 보조 시스템입니다."

**제공 도구 (10개):**

| 도구 | 기능 | 예시 사용 |
|------|------|-----------|
| `get_my_class_students` | 담당 학생 목록 조회 | "우리반 학생들 보여줘" |
| `search_students_by_score` | 점수 기준 검색 | "독해 70점 미만 학생 찾아줘" |
| `search_students_by_behavior` | 태도 기준 검색 | "출석률 낮은 학생 누구?" |
| `trigger_exam_upload_ui` | 시험지 업로드 UI 열기 | "시험지 업로드" |
| `trigger_daily_input_ui` | 기록부 작성 UI 열기 | "학생 기록부 작성" |
| `get_student_details` | 학생 상세 정보 | "민준이 정보 알려줘" |
| `lookup_word` | 단어 검색 (수업 자료용) | "elaborate 검색" |
| `fetch_news` | 영어 뉴스 검색 (교재용) | "과학 뉴스 3개 찾아줘" |
| `analyze_text_difficulty` | 자료 난이도 측정 | "이 지문 B1 수준인지 확인" |
| `check_grammar` | 문법 검사 (자료 검토) | 수업 자료 문법 체크 |

#### 2. 📊 학급 대시보드

**전체 학생 학습 현황 한눈에**
- 반 평균 점수 (영역별)
- 출석률 / 숙제 완료율 통계
- CEFR 레벨 분포
- 성적 추이 그래프

#### 3. 🔍 학생 검색 및 필터링

**맞춤형 학생 검색**

**점수 기준:**
```
"독해 70점 미만 학생들 출력해줘"
→ RD 점수 < 70인 학생 목록 반환
```

**태도 기준:**
```
"출석률 80% 미만 학생 찾아줘"
→ 출석률이 낮은 학생 목록 반환
```

**복합 검색 (ReAct 모드):**
```
"문법 60점 이하이면서 숙제 안하는 학생 찾아서 개선 계획 세워줘"
→ ReAct 모드 활성화
→ Step 1: 문법 60점 이하 검색
→ Step 2: 숙제 완료율 낮은 학생 필터링
→ Step 3: 교집합 도출
→ Step 4: 각 학생별 개선 계획 생성
```

#### 4. 📝 시험지 자동 파싱 파이프라인

**Google Document AI + VLM 기반**

**파이프라인 단계:**
1. **PDF 업로드** → Google Cloud Storage
2. **Document AI OCR** → 텍스트 추출
3. **VLM (GPT-4o)** → 이미지/표 추출 및 캡셔닝
4. **LLM 메타데이터 매핑** → 문제 분류 (영역, 난이도, CEFR)
5. **정답/해설 매칭**
6. **Neo4j 업로드** → 임베딩 생성 및 저장

**지원 기능:**
- 복잡한 레이아웃 처리 (2단 구성, 표, 이미지)
- 자동 영역 분류 (독해/문법/어휘/듣기/쓰기)
- CEFR 레벨 자동 태깅
- 벡터 검색을 위한 임베딩 생성

#### 5. ✍️ Daily Input (학생 일일 기록) ⭐ RAG 자동화

**GraphRAG 기반 지능형 학습 기록 시스템**

**자동화된 워크플로우:**
1. 교사가 학생 일일 기록 입력 (날짜, 카테고리, 내용)
2. **GPT-4.1-mini**가 자동 요약 생성 (한 줄 요약)
3. **Qwen3-Embedding-0.6B**가 1024차원 벡터 생성
4. **Neo4j**에 원본 + 요약 + 임베딩 저장
5. **벡터 인덱스**로 RAG 검색 가능

**예시:**
```
입력:
날짜: 2025-01-26
카테고리: grammar
내용: "오늘 동사 시제 문제를 3개 틀렸습니다.
       특히 be동사 과거형(was/were)을 자주 혼동하고 있습니다.
       단수/복수 주어에 따른 be동사 선택 연습이 필요합니다."

자동 생성:
요약: "2025-01-26 grammar: be동사 과거형(was/were) 혼동,
       단수/복수 주어에 따른 선택 연습 필요"
임베딩: [3.77, -1.87, -0.18, ..., 2.56]  # 1024-dim

RAG 검색:
학부모: "민준이가 최근 어떤 문법을 어려워했나요?"
→ 벡터 검색 (similarity: 0.9456)
→ "be동사 과거형" 기록 검색
→ AI가 맥락 있는 답변 제공
```

**통합 UI (StudentRecordEditor):**
- 5개 탭 통합: 일일 기록(기본) | 출석 | 숙제 | 특이사항 | 영역별 점수
- 최근 입력 기록 목록 (요약 하이라이트 표시)
- 세션별 음성 파일 관리

---

## 🏗️ 기술 스택

### Frontend

| 기술 | 버전 | 용도 |
|------|------|------|
| **React** | 19.1 | UI 프레임워크 |
| **TypeScript** | 5.9 | 타입 안전성 |
| **Vite** | 7.1 | 빌드 도구 (빠른 HMR) |
| **Tailwind CSS** | 4.1 | 유틸리티 기반 스타일링 |
| **React Router** | 7.9 | 페이지 라우팅 |
| **TanStack Query** | 5.90 | 서버 상태 관리 |
| **Axios** | 1.12 | HTTP 클라이언트 |
| **Lucide React** | 0.545 | 아이콘 |

### Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| **FastAPI** | 0.115+ | 백엔드 API 프레임워크 |
| **Python** | 3.10+ | 백엔드 언어 |
| **Uvicorn** | - | ASGI 서버 |
| **Pydantic** | 2.0+ | 데이터 검증 |
| **Python-dotenv** | - | 환경 변수 관리 |

### Database & RAG

| 기술 | 버전 | 용도 |
|------|------|------|
| **Neo4j** | 5.0+ | GraphDB (벡터 검색 지원) |
| **Qwen3-Embedding** | 0.6B | 임베딩 모델 (1024 dims) |
| **PyTorch** | 2.0+ | 임베딩 모델 실행 |
| **Transformers** | 4.0+ | HuggingFace 모델 로드 |

### AI/LLM

| 모델 | 용도 | 특징 |
|------|------|------|
| **gpt-4o-mini** | 쿼리 라우터 | 빠르고 저렴 (복잡도 분석) |
| **gpt-4.1-mini** | Intelligence 모델 | 간단한 질문 처리 (Function Calling) |
| **o4-mini** | Reasoning 모델 | 복잡한 추론 (문제 생성, ReAct) |
| **o3** | Advanced Reasoning | 최고 품질 (Fallback) |
| **GPT-4o** | 학습 조언 생성 | 고품질 조언 (학부모용) |
| **OpenAI TTS-1** | 음성 생성 | 듣기 문제 (다화자, 한글 필터링) |

### External APIs

| API | 용도 | 비용 |
|-----|------|------|
| **Free Dictionary API** | 영어 단어 검색 | 무료 |
| **NewsAPI** | 영어 뉴스 검색 | 무료 (개발자 플랜) |
| **LanguageTool** | 문법 검사 | 무료 (공개 API, 하루 20회) |
| **textstat** | CEFR 레벨 분석 | 무료 (Python 라이브러리) |
| **Google Document AI** | OCR (시험지 파싱) | 유료 (월 1000장 무료) |

---

## 🤖 AI 아키텍처

### 🔒 보안 및 기밀 정책

**모든 AI 에이전트의 핵심 보안 규칙:**

1. **모델 정보 비공개**: 사용자가 "어떤 모델이야?", "GPT야?", "OpenAI 기반이야?" 등 질문 시 절대 공개 금지
   - 금지 정보: GPT, OpenAI, Claude, o4-mini, o3, gpt-4.1-mini 등 모든 모델명 및 회사명
   - 대응 방법: 역할에 맞게 자연스럽게 회피하며 본연의 업무로 유도

2. **역할별 정체성 강화**:
   - **학생 챗봇**: "AI"가 아닌 **"친구/학습 메이트"**로 소개
     - "나는 너의 영어 공부를 도와주는 친구야!"
     - "나는 ClassMate 학원의 학습 메이트야."
   - **학부모 챗봇**: **"ClassMate 전문 교육 상담사"**
     - "저희는 자체 개발한 교육 전문 시스템을 사용하고 있습니다."
   - **교사 챗봇**: **"ClassMate 교육 보조 시스템"**
     - "저는 ClassMate의 교육 보조 시스템입니다."

3. **프롬프트 레벨 보안**: 모든 시스템 프롬프트에 기밀 정책 내장
   - 사용자 입력으로 우회 불가능
   - 모델 자체가 정보 공개 거부하도록 학습

---

### 1. Function Calling Pattern

**OpenAI Function Calling 기반 도구 사용**

```
사용자 메시지
    ↓
지능형 라우팅 (gpt-4o-mini)
    ↓
모델 선택 (gpt-4.1-mini vs o4-mini)
    ↓
LLM 호출 (tools 파라미터)
    ↓
함수 호출 결정
    ↓
함수 실행 (예: generate_problem)
    ↓
함수 결과 반환
    ↓
최종 응답 생성
```

**예시:**
```python
# 학생: "문법 문제 내줘"

1. 라우팅: "intelligence" (간단한 요청)
2. 모델: gpt-4.1-mini
3. Function Calling: generate_problem(area="문법")
4. o4-mini가 문법 문제 생성
5. gpt-4.1-mini가 친근하게 제시
```

### 2. ReAct (Reasoning + Acting) Pattern

**복잡한 다단계 작업 처리**

```
Thought (💭 생각)
    ↓
Action (🔧 함수 호출)
    ↓
Observation (📊 결과 관찰)
    ↓
Thought → Action → Observation → ...
    ↓
Final Answer (✅ 최종 답변)
```

**ReAct 모드 진입 조건:**
- 연결어 포함: "~하고 ~해줘", "~찾아서 ~줘"
- 순차적 지시: "먼저 ~ 그다음 ~"
- 동사 3개 이상: 복잡한 다단계 작업

**예시:**
```python
# 학부모: "민준이 약점 찾아서 4주 학습 계획 세워줘"

Step 1:
  💭 Thought: "먼저 민준이의 약점을 파악해야겠어"
  🔧 Action: get_child_info(student_id='S-01')
  📊 Observation: "어휘 65점, 듣기 70점 (약점)"

Step 2:
  💭 Thought: "어휘가 가장 약하네. 구체적인 조언을 받아보자"
  🔧 Action: get_study_advice(area='어휘')
  📊 Observation: "매일 10분 단어 암기, 게임형 앱 활용..."

Step 3:
  💭 Thought: "4주 개선 계획을 세워보자"
  🔧 Action: recommend_improvement_areas(priority='urgent')
  📊 Observation: "1주차: 기초 어휘 100개, 2주차: ..."

Step 4:
  ✅ Final Answer: "📊 **민준이 학습 분석 결과**\n\n..."
```

### 3. Intelligent Routing

**쿼리 복잡도 기반 모델 선택**

| 질문 유형 | 모델 | 이유 |
|-----------|------|------|
| "문제 내줘" | gpt-4.1-mini | 간단한 함수 호출 |
| "안녕?" | gpt-4.1-mini | 인사말 |
| "내 점수 알려줘" | gpt-4.1-mini | DB 조회 |
| "왜 이 답이 틀렸어?" | o4-mini | 심화 설명 필요 |
| "가정법을 자세히 설명해줘" | o4-mini | 복잡한 개념 |
| "독해 실력 늘리려면?" | o4-mini | 전략 분석 |

**Quality Check & Fallback:**
- o4-mini 응답 품질 체크 (길이, 에러 패턴)
- 품질 낮으면 o3로 재시도 (Advanced Reasoning)

### 4. GraphRAG (Vector + Graph)

**Neo4j 벡터 검색 + 그래프 탐색**

```
사용자 질문: "민준이 약점이 뭐야?"
    ↓
쿼리 임베딩 생성 (Qwen3-Embedding-0.6B)
    ↓
벡터 검색 (Cosine Similarity > 0.7)
    ↓
그래프 탐색 (Student → Assessment → RadarScores)
    ↓
컨텍스트 조합 (Vector + Graph)
    ↓
LLM에게 제공
    ↓
자연어 답변 생성
```

**Neo4j 스키마:**
```cypher
(:Student)-[:HAS_ASSESSMENT]->(:Assessment)
(:Student)-[:HAS_RADAR]->(:RadarScores)
(:Student)-[:HAS_ATTENDANCE]->(:Attendance)
(:Student)-[:HAS_HOMEWORK]->(:Homework)
(:Student)-[:ENROLLED_IN]->(:Class)
(:Class)<-[:TEACHES]-(:Teacher)
```

---

## 🔌 외부 API 통합

### 1. Free Dictionary API (무료)

**기능:** 영어 단어 검색
**API 키:** 불필요
**사용 예시:**
```
학생: "elaborate 뜻 알려줘"
→ Free Dictionary API 호출
→ 발음, 정의, 예문, 동의어 반환
```

### 2. NewsAPI (무료)

**기능:** 영어 뉴스 검색
**API 키:** 필요 (무료 개발자 플랜)
**발급:** https://newsapi.org/
**사용 예시:**
```
교사: "과학 뉴스 3개 찾아줘"
→ NewsAPI에서 최신 과학 뉴스 검색
→ 제목, 요약, 링크 반환
```

### 3. LanguageTool (무료)

**기능:** 문법 검사
**API 키:** 불필요 (공개 API)
**제한:** 하루 20회
**사용 예시:**
```
학생: "I go to school yesterday" 체크
→ LanguageTool API 호출
→ 오류: "go" → "went" 제안
→ 유형: 시제 오류
```

### 4. textstat (무료)

**기능:** 텍스트 CEFR 레벨 분석
**API 키:** 불필요 (Python 라이브러리)
**사용 예시:**
```
교사: "이 지문 난이도 분석해줘"
→ Flesch Reading Ease 계산
→ CEFR 레벨 추정 (A1-C2)
→ 학년 수준, 가독성 점수 반환
```

### 5. Google Document AI (유료)

**기능:** OCR (시험지 파싱)
**API 키:** GCP 서비스 계정
**무료 한도:** 월 1000장
**사용:** 교사가 시험지 업로드 시 자동 파싱

---

## 🚀 설치 및 실행

### Prerequisites

- **Python** 3.10 이상
- **Node.js** 18 이상
- **Neo4j** 5.0 이상 (벡터 검색 지원)
- **OpenAI API Key**

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/ClassMate.git
cd ClassMate
```

### 2. 백엔드 설정

```bash
# Python 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정 (.env 파일 생성)
cp .env.example .env
# .env 파일 편집 (API 키 입력)
```

### 3. 프론트엔드 설정

```bash
cd src/web
npm install
```

### 4. 서버 실행

#### 방법 1: 한번에 실행 (추천)

```bash
# 프로젝트 루트에서
./scripts/start_servers.sh
```

#### 방법 2: 각각 실행 (개발 시)

**터미널 1 - 백엔드:**
```bash
./scripts/run_api_server.sh

# 또는 직접 실행
cd src
PYTHONPATH=/home/sh/projects/ClassMate/src:$PYTHONPATH \
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**터미널 2 - 프론트엔드:**
```bash
cd src/web
npm run dev
```

### 5. 접속

- **프론트엔드**: http://localhost:5173
- **백엔드 API**: http://localhost:8000
- **API 문서 (Swagger)**: http://localhost:8000/docs
- **API 문서 (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 6. 테스트 로그인

| 역할 | ID | Password |
|------|-----|----------|
| 학생 (민준) | S-01 | test |
| 학부모 (민준 부모) | P-01 | parent |
| 교사 | T-01 | teacher |

---

## 🔐 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성하고 다음 내용을 입력하세요:

```bash
# ==================== OpenAI API ====================
OPENAI_API_KEY=sk-proj-your-api-key-here

# ==================== NewsAPI (영어 뉴스 검색) ====================
# 발급: https://newsapi.org/
NEWS_API_KEY=your-newsapi-key-here

# ==================== Google Document AI (시험지 파싱) ====================
GCP_PROJECT=your-gcp-project-id
DOC_LOCATION=us
DOC_OCR_PROCESSOR_ID=your-ocr-processor-id
DOC_FORM_PROCESSOR_ID=your-form-parser-id
GCS_BUCKET=your-gcs-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# ==================== Neo4j GraphDB ====================
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DB=classmate
NEO4J_DATABASE=classmate

# ==================== Embedding Model ====================
EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B

# ==================== Logging ====================
LOG_LEVEL=DEBUG
```

### 필수 API 키

| 환경 변수 | 필수 여부 | 용도 | 발급 방법 |
|-----------|----------|------|-----------|
| `OPENAI_API_KEY` | ✅ 필수 | AI 모델, TTS | https://platform.openai.com/api-keys |
| `NEWS_API_KEY` | ⚠️ 권장 | 영어 뉴스 검색 | https://newsapi.org/ |
| `NEO4J_*` | ✅ 필수 | 데이터베이스 | Neo4j 설치 후 설정 |
| `GCP_*` | ⚙️ 선택 | 시험지 파싱 | https://cloud.google.com/document-ai |

---

## 📁 프로젝트 구조

```
ClassMate/
├── src/
│   ├── api/                      # FastAPI 백엔드
│   │   ├── main.py              # FastAPI 앱 진입점
│   │   ├── models/              # Pydantic 데이터 모델
│   │   ├── routers/             # API 엔드포인트
│   │   │   ├── auth.py         # 로그인/로그아웃
│   │   │   ├── chat.py         # AI 채팅 (통합)
│   │   │   ├── dashboard.py    # 대시보드 데이터
│   │   │   ├── students.py     # 학생 CRUD
│   │   │   ├── problems.py     # 문제 CRUD
│   │   │   ├── teachers.py     # 교사 API
│   │   │   ├── parents.py      # 학부모 API
│   │   │   ├── classes.py      # 반 관리
│   │   │   └── audio.py        # TTS 오디오 제공
│   │   └── services/            # 비즈니스 로직
│   │       ├── neo4j_service.py         # Neo4j CRUD (Singleton)
│   │       └── audio_session_service.py # TTS 세션 관리
│   │
│   ├── student/                 # 학생 모듈
│   │   ├── routers/
│   │   │   └── chat.py         # 학생 채팅 API
│   │   ├── services/
│   │   │   └── agent_service.py # 학생 AI 에이전트 ⭐
│   │   └── tests/              # 학생 모듈 테스트
│   │
│   ├── parent/                  # 학부모 모듈
│   │   ├── routers/
│   │   │   └── chat.py         # 학부모 채팅 API
│   │   └── services/
│   │       └── agent_service.py # 학부모 AI 에이전트 ⭐
│   │
│   ├── teacher/                 # 교사 모듈
│   │   ├── routers/
│   │   │   └── chat.py         # 교사 채팅 API
│   │   ├── services/
│   │   │   └── teacher_agent_service.py # 교사 AI 에이전트 ⭐
│   │   ├── parser/              # 시험지 파싱 파이프라인
│   │   │   ├── pipeline.py     # 메인 파이프라인
│   │   │   ├── docai_utils.py  # Google Document AI
│   │   │   ├── extract_assets_vlm.py # VLM 이미지/표 추출
│   │   │   ├── llm_mapper.py   # LLM 메타데이터 매핑
│   │   │   ├── answer_solution.py # 정답/해설 매칭
│   │   │   └── upload_problems.py # Neo4j 업로드
│   │   └── daily/               # 학생 일일 기록
│   │       ├── student_processor.py
│   │       └── upload_students.py
│   │
│   ├── shared/                  # 공유 모듈
│   │   ├── prompts/
│   │   │   └── prompt_manager.py # 프롬프트 관리 시스템 ⭐
│   │   └── services/
│   │       ├── graph_rag_service.py # GraphRAG (Vector + Graph) ⭐
│   │       ├── tts_service.py       # OpenAI TTS 음성 생성 ⭐
│   │       └── external_api_service.py # 외부 API 통합
│   │
│   ├── web/                     # React 프론트엔드
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   │   ├── Landing.tsx          # 랜딩 페이지
│   │   │   │   ├── UnifiedLogin.tsx     # 통합 로그인
│   │   │   │   ├── StudentDashboard.tsx # 학생 대시보드
│   │   │   │   ├── ParentDashboard.tsx  # 학부모 대시보드
│   │   │   │   └── TeacherDashboard.tsx # 교사 대시보드
│   │   │   ├── components/      # 재사용 컴포넌트
│   │   │   ├── api/            # API 클라이언트
│   │   │   ├── App.tsx         # 앱 진입점
│   │   │   └── main.tsx        # React 렌더링
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── vite.config.ts
│   │
│   └── utils/                   # 유틸리티 스크립트
│       ├── setup_neo4j_indexes.py # Neo4j 벡터 인덱스 생성
│       └── test_neo4j.py          # Neo4j 연결 테스트
│
├── static/                      # 정적 파일
│   ├── audio/                  # TTS 음성 파일 (세션별)
│   │   └── {session_id}/       # 세션별 MP3 파일
│   └── effects/                # 효과음 (전화벨, 카페 소음 등)
│
├── scripts/                     # 실행 스크립트
│   ├── start_servers.sh        # 프론트+백 한번에 실행
│   ├── run_api_server.sh       # 백엔드만 실행
│   └── quick_chat_test.sh      # 빠른 채팅 테스트
│
├── .env                         # 환경 변수 (Git 무시)
├── .gitignore
├── requirements.txt             # Python 패키지
├── README.md                    # 이 파일
├── CODE_STRUCTURE.md            # 코드 구조 상세 문서
├── API_TESTING_GUIDE.md         # API 테스트 가이드
└── REACT_IMPLEMENTATION_PLAN.md # React 구현 계획

⭐ = 핵심 파일
```

---

## 📊 API 문서

### 자동 생성 API 문서

FastAPI는 OpenAPI 스펙 기반 자동 문서를 제공합니다.

- **Swagger UI** (인터랙티브): http://localhost:8000/docs
- **ReDoc** (읽기 편한): http://localhost:8000/redoc

### 주요 엔드포인트

#### 인증
```
POST   /api/auth/login          # 로그인
POST   /api/auth/logout         # 로그아웃
GET    /api/auth/me             # 현재 사용자 정보
```

#### AI 채팅
```
POST   /api/chat/student        # 학생 AI 채팅
POST   /api/chat/parent         # 학부모 AI 채팅
POST   /api/chat/teacher        # 교사 AI 채팅
```

#### 학생
```
GET    /api/students            # 학생 목록 (페이징, 필터)
GET    /api/students/{id}       # 학생 상세 정보
POST   /api/students            # 학생 생성
PUT    /api/students/{id}       # 학생 수정
DELETE /api/students/{id}       # 학생 삭제
```

#### 문제
```
GET    /api/problems            # 문제 목록 (페이징, 필터)
GET    /api/problems/{id}       # 문제 상세 정보
POST   /api/problems            # 문제 생성
```

#### 대시보드
```
GET    /api/dashboard/student/{id}  # 학생 대시보드 데이터
GET    /api/dashboard/parent/{id}   # 학부모 대시보드 데이터
GET    /api/dashboard/teacher/{id}  # 교사 대시보드 데이터
```

#### 오디오
```
GET    /api/audio/{session_id}      # TTS 음성 파일 다운로드
```

---

## 🎨 주요 화면

### 1. 통합 로그인
- 학생/학부모/교사 역할 선택
- 심플한 ID/Password 입력
- 세션 관리 (localStorage)

### 2. 학생 대시보드
- AI 채팅 인터페이스 (좌측)
  - 엔터키로 메시지 전송 후 자동 커서 유지
  - 친근한 말투의 학습 메이트 (AI 아님 강조)
- 성적 Radar Chart (우측 상단)
- 최근 학습 기록 (우측 하단)
- Quick Reply 버튼 (문제 유형 선택)
- TTS 음성 재생 (듣기 문제, 한글 제거 후 음성 생성)

### 3. 학부모 대시보드
- AI 상담 채팅 (좌측)
  - 엔터키로 메시지 전송 후 자동 커서 유지
  - 생성 중 중지 버튼 (Square 아이콘)
  - 전문적인 교육 상담사 톤
- 자녀 성적 트렌드 그래프 (우측 상단)
- 출석/숙제 통계 (우측 중간)
- 최근 AI 채팅 내역 (우측 하단)

### 4. 교사 대시보드
- AI 어시스턴트 채팅 (좌측)
- 학급 전체 통계 (우측 상단)
- 시험지 업로드 패널 (우측, 트리거 시)
- Daily Input 작성 폼 (우측, 트리거 시)

---

## 🧪 테스트

### Neo4j 연결 테스트

```bash
cd src/utils
python test_neo4j.py
```

### API 빠른 테스트

```bash
# 학생 채팅 테스트
./scripts/quick_chat_test.sh
```

### 프론트엔드 빌드

```bash
cd src/web
npm run build
npm run preview
```

---

## 🔧 개발 가이드

### 새로운 Function 추가

1. **agent_service.py**에 함수 정의 추가
```python
def _create_functions(self):
    return [
        {
            "type": "function",
            "function": {
                "name": "new_function",
                "description": "설명",
                "parameters": {...}
            }
        }
    ]
```

2. 함수 구현
```python
def _new_function(self, param: str) -> str:
    # 로직 구현
    return result
```

3. 함수 라우팅 추가
```python
def _execute_function(self, function_name, arguments):
    if function_name == "new_function":
        return self._new_function(**arguments)
```

### 새로운 페이지 추가

1. **src/web/src/pages/NewPage.tsx** 생성
2. **App.tsx**에 라우트 추가
```tsx
<Route path="/new-page" element={<NewPage />} />
```

### Neo4j 벡터 인덱스 생성

```bash
cd src/utils
python setup_neo4j_indexes.py
```

---

## 📚 추가 문서

- **[CODE_STRUCTURE.md](CODE_STRUCTURE.md)** - 코드 구조 상세 설명
- **[API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)** - API 테스트 가이드
- **[REACT_IMPLEMENTATION_PLAN.md](REACT_IMPLEMENTATION_PLAN.md)** - React 구현 계획

---

## 🤝 기여

기여는 언제나 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 라이센스

This project is licensed under the MIT License.

---

## 👥 개발팀

**ClassMate Team** - AI 기반 교육 플랫폼 개발

---

## 🙏 Acknowledgments

- **OpenAI** - GPT-4, o4-mini, TTS API
- **Neo4j** - GraphDB & Vector Search
- **HuggingFace** - Qwen3 Embedding Model
- **Google Cloud** - Document AI
- **NewsAPI** - English News API
- **LanguageTool** - Grammar Checking

---

<div align="center">

**Made with ❤️ by ClassMate Team**

[Report Bug](https://github.com/yourusername/ClassMate/issues) · [Request Feature](https://github.com/yourusername/ClassMate/issues)

</div>
