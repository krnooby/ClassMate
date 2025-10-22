# ClassMate Web Frontend

React + TypeScript + Vite 기반 프론트엔드

## 🚀 실행 방법

### 1. 의존성 설치 (최초 1회)
```bash
cd src/web
npm install
```

### 2. 개발 서버 실행
```bash
cd src/web
npm run dev
```

기본 포트: http://localhost:5173

### 3. 백엔드 API 서버 실행
프론트엔드가 동작하려면 백엔드 API 서버가 실행 중이어야 합니다.

**터미널 1 (백엔드):**
```bash
cd /home/sh/projects/ClassMate
./run_api_server.sh
```

**터미널 2 (프론트엔드):**
```bash
cd src/web
npm run dev
```

---

## 📁 프로젝트 구조

```
src/web/
├── src/
│   ├── api/              # API 클라이언트
│   │   ├── client.ts     # Axios 설정
│   │   └── services.ts   # API 서비스 함수
│   ├── pages/            # 페이지 컴포넌트
│   │   ├── Dashboard.tsx # 대시보드
│   │   ├── Students.tsx  # 학생 목록/검색
│   │   └── Problems.tsx  # 문제 검색
│   ├── components/       # 재사용 컴포넌트 (추후 추가)
│   ├── hooks/            # Custom hooks (추후 추가)
│   ├── types/            # TypeScript 타입 정의
│   │   └── index.ts
│   ├── utils/            # 유틸리티 함수 (추후 추가)
│   ├── App.tsx           # 메인 앱 (라우팅)
│   ├── main.tsx          # 진입점
│   └── index.css         # Tailwind CSS
├── .env                  # 환경 변수
├── tailwind.config.js    # Tailwind 설정
├── postcss.config.js     # PostCSS 설정
├── vite.config.ts        # Vite 설정
└── package.json          # 의존성

```

---

## 🎨 주요 기능

### ✅ 구현 완료

#### 1. Dashboard (대시보드)
- 전체 통계 (문제, 학생, 자산)
- 영역별 문제 분포
- 난이도별 문제 분포
- 학생 CEFR 레벨 분포
- **URL:** `/`

#### 2. Students (학생 관리)
- 학생 목록 (페이징)
- 임베딩 기반 유사 학생 검색
- 학생 카드 (출석률, CEFR, 백분위 등)
- **URL:** `/students`

#### 3. Problems (문제 검색)
- 문제 목록 (페이징)
- 필터링 (영역, 난이도, CEFR)
- 임베딩 기반 유사 문제 검색
- 문제 카드 (문항, 보기, 정답, 자산)
- **URL:** `/problems`

### 🔜 추후 구현 예정
- 학생 상세 페이지
- 문제 상세 페이지
- 차트 라이브러리 (Chart.js / Recharts)
- 파일 업로드 UI
- 인증/로그인
- 다크 모드

---

## 🛠️ 기술 스택

- **React 18** - UI 라이브러리
- **TypeScript** - 타입 안전성
- **Vite** - 빌드 도구
- **React Router** - 라우팅
- **TanStack Query (React Query)** - 데이터 fetching
- **Axios** - HTTP 클라이언트
- **TailwindCSS** - CSS 프레임워크
- **Lucide React** - 아이콘

---

## 🔧 개발 가이드

### API Base URL 변경
`.env` 파일 수정:
```env
VITE_API_BASE_URL=http://localhost:8000
```

### 새 페이지 추가
1. `src/pages/NewPage.tsx` 생성
2. `src/App.tsx`에 라우트 추가:
```tsx
<Route path="/new-page" element={<NewPage />} />
```

### 새 API 엔드포인트 추가
1. `src/types/index.ts`에 타입 정의
2. `src/api/services.ts`에 API 함수 추가

---

## 🧪 빌드 및 배포

### 개발 빌드
```bash
npm run dev
```

### 프로덕션 빌드
```bash
npm run build
```

빌드 결과: `dist/` 디렉토리

### 프리뷰
```bash
npm run preview
```

---

## 🐛 트러블슈팅

### 1. 백엔드 연결 실패
**증상:** API 호출 시 Network Error

**확인:**
```bash
curl http://localhost:8000/health
```

**해결:** 백엔드 서버가 실행 중인지 확인
```bash
./run_api_server.sh
```

### 2. CORS 에러
**증상:** Cross-Origin Request Blocked

**해결:** 백엔드 `src/api/main.py`의 CORS 설정 확인:
```python
allow_origins=[
    "http://localhost:5173",  # Vite 개발 서버
]
```

### 3. 포트 충돌
**증상:** Port 5173 is already in use

**해결:** 다른 포트 사용:
```bash
npm run dev -- --port 3000
```

---

## 📝 다음 단계

1. **차트 추가**
   - Chart.js 또는 Recharts 설치
   - Dashboard에 시각화 개선

2. **상세 페이지**
   - 학생 상세 페이지
   - 문제 상세 페이지

3. **인증 시스템**
   - 로그인/로그아웃
   - JWT 토큰 관리

4. **파일 업로드**
   - PDF 업로드 UI
   - 파이프라인 트리거

---

**버전:** 1.0.0
**최종 업데이트:** 2025-10-16
