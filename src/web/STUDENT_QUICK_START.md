# 🎓 학생 대시보드 빠른 시작

## ✨ Neo4j 없이 작동합니다!

현재는 `students_rag.json` 파일에서 직접 데이터를 읽어옵니다.
Neo4j 연결 없이도 완벽하게 작동합니다.

---

## 1️⃣ 서버 실행

### 백엔드 (터미널 1)
```bash
./run_api_server.sh
```

### 프론트엔드 (터미널 2)
```bash
cd src/web && npm run dev
```

## 2️⃣ 접속 및 로그인

1. **URL**: http://localhost:5173/student-dashboard
2. **학생 ID**: S-01, S-02, S-03 등
3. **비밀번호**: test
4. **로그인** 클릭

## 3️⃣ 대시보드 확인

- ✅ CEFR 레벨, 출석률, 백분위, 숙제 완료율
- ✅ 반 정보 및 최근 활동 (학습 진도, 숙제, 월말 시험)
- ✅ 영역별 점수 차트
- ✅ 학생 정보 및 학습 요약

---

## ⚠️ 문제 해결

### "존재하지 않는 학생 ID"
**원인:** 학생 ID 형식이 잘못되었습니다.

**올바른 형식:**
- `S-01`, `S-02`, `S-03`, ... (하이픈 포함)
- ❌ `S01`, `s-01` (잘못된 형식)

**테스트 가능한 학생 ID:**
```
S-01 (김민준)
S-02, S-03, S-04, ... S-40
```

### 백엔드 서버 연결 실패
```bash
# 서버가 실행 중인지 확인
curl http://localhost:8000/health

# 재시작
pkill -f "uvicorn api.main"
./run_api_server.sh
```

### 학생 데이터가 없음
**원인:** `students_rag.json` 파일이 없거나 경로가 잘못됨

**확인:**
```bash
ls -la /home/sh/projects/ClassMate/data/json/students_rag.json
```

---

**상세 가이드:** STUDENT_DASHBOARD_GUIDE.md
