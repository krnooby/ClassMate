# Neo4j 임베딩 생성 가이드

## 📌 개요

Neo4j 그래프 데이터베이스의 노드에 Qwen3-Embedding-0.6B 모델을 사용하여 벡터 임베딩을 생성합니다.

**최근 수정 사항 (2025-10-19):**
- ✅ 임베딩 순환 참조 방지 (기존 임베딩 벡터가 다시 임베딩되는 문제 해결)
- ✅ `max_length=2048` 설정 (Curriculum 등 긴 텍스트 대응)
- ✅ 성능 최적화: **60배 속도 향상** (23,000자 → 100자)

---

## 🚀 빠른 시작

### 로컬 환경 (CPU/GPU 자동 감지)

```bash
./run_embedding.sh
```

### 팀원 환경 (RTX 4070 최적화)

```bash
./run_embedding_team.sh
```

---

## 📋 사전 요구사항

### 1. Python 패키지
```bash
pip install torch transformers neo4j python-dotenv tqdm
```

### 2. 환경 변수 (`.env` 파일)
```bash
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B
LOG_LEVEL=INFO
```

### 3. Neo4j 실행 중
```bash
# 연결 테스트
python3 src/utils/test_neo4j.py
```

---

## ⚙️ 설정 옵션

### `embedding.py` 실행 옵션

```bash
python3 embedding.py [옵션]

--batch <N>              # 배치 크기 (기본: 4, GPU 권장: 16)
--gpu-clear-interval <N> # GPU 캐시 정리 주기 (기본: 100)
--rel-summary <N>        # 관계 정보 포함 수 (기본: 0, 권장: 0)
--labels <LABEL> ...     # 처리할 노드 라벨 (미지정 시 전체)
--limit <N>              # 각 라벨당 최대 노드 수 (0=전체)
--log-level <LEVEL>      # 로그 레벨 (DEBUG/INFO/WARNING/ERROR)
```

### GPU 메모리별 배치 크기 권장

| GPU VRAM | 배치 크기 | GPU Clear Interval |
|----------|-----------|-------------------|
| 12GB (RTX 4070) | 16 | 150 |
| 8GB | 12 | 100 |
| 6GB | 8 | 80 |
| CPU | 4 | 50 |

---

## 📊 처리 대상 노드

기본 라벨 목록 (`embedding.py:17-20`):
- `Assessment`, `Attendance`, `Class`, `Curriculum`
- `Fig`, `Homework`, `Notes`, `Parent`
- `PeerDistribution`, `Problem`, `RadarScores`
- `Student`, `Tbl`, `TblRow`, `Teacher`

### 특정 라벨만 처리하기

```bash
# Student와 Problem만 임베딩
python3 embedding.py --labels Student Problem --batch 16
```

---

## 🔍 진행 상황 확인

### 실시간 로그 확인
```bash
tail -f embedding_20251019_*.log
```

### Neo4j에서 임베딩 확인
```cypher
// 임베딩된 Student 노드 수
MATCH (s:Student)
WHERE s.embedding IS NOT NULL
RETURN count(s)

// 최근 임베딩된 노드
MATCH (n)
WHERE n.embedding IS NOT NULL
RETURN labels(n)[0] AS label,
       n.embedding_ts AS timestamp,
       n.embedding_dim AS dimension
ORDER BY timestamp DESC
LIMIT 10
```

---

## ⚡ 성능 최적화

### 1. 임베딩 순환 참조 방지
이전에 생성된 `embedding` 속성(23,000자)이 다시 임베딩되는 문제 해결:

```python
# embedding.py:49-50
SKIP_KEYS = {'embedding', 'embedding_model', 'embedding_dim', ...}
```

### 2. 텍스트 길이 제한
```python
# embedding.py:187
max_length=2048  # Curriculum 616 토큰 대응
```

### 3. GPU 메모리 관리
```bash
# GPU 캐시 주기적 정리
--gpu-clear-interval 150
```

---

## 🐛 트러블슈팅

### 문제 1: "Long text detected: len=23000+"
**원인:** 이미 생성된 임베딩 벡터가 텍스트에 포함됨
**해결:** 수정된 `embedding.py` 사용 (SKIP_KEYS 적용)

### 문제 2: CUDA Out of Memory
**해결:**
```bash
# 배치 크기 줄이기
--batch 8 --gpu-clear-interval 50

# 또는 CPU 모드
CUDA_VISIBLE_DEVICES="" python3 embedding.py --batch 4
```

### 문제 3: Neo4j 연결 실패
**확인 사항:**
- Neo4j 서버 실행 중인지 확인
- `.env` 파일의 인증 정보 확인
- 방화벽 설정 확인 (포트 7687)

### 문제 4: 중단 후 재시작
**안전합니다!**
- 이미 처리된 노드는 DB에 저장됨
- 재실행 시 기존 임베딩 덮어쓰기
- 중복 걱정 없음

---

## 📝 로그 예시

### 정상 실행
```
2025-10-19 10:30:15 | INFO | starting embedding job
2025-10-19 10:30:15 | INFO | model=Qwen/Qwen3-Embedding-0.6B device=cuda
2025-10-19 10:30:20 | INFO | embedding_dim=768
2025-10-19 10:30:21 | INFO | vector_index Student: exists
2025-10-19 10:30:21 | INFO | Student: total=40 batch=16
Student: 100%|███████████| 40/40 [00:08<00:00, 4.8 n/s]
2025-10-19 10:30:29 | INFO | Student: +16 in 2.1s (7.6 n/s) progress=16/40
2025-10-19 10:30:31 | INFO | Student: +16 in 2.0s (8.0 n/s) progress=32/40
2025-10-19 10:30:33 | INFO | Student: +8 in 1.2s (6.7 n/s) progress=40/40
2025-10-19 10:30:33 | INFO | Student: all batches completed successfully
```

---

## 📚 관련 문서

- [프로젝트 README](README.md)
- [Neo4j 설정 가이드](docs/neo4j_setup.md)
- [API 문서](docs/api/API_README.md)

---

## 🆘 문제 해결

문제가 지속되면:
1. 로그 파일 확인 (`embedding_*.log`)
2. Neo4j 브라우저에서 데이터 확인 (http://localhost:7474)
3. GitHub Issues 등록

---

**마지막 업데이트:** 2025-10-19
**버전:** 1.1.0 (순환 참조 수정)
