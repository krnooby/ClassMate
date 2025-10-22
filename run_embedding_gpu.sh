#!/bin/bash
# Neo4j 임베딩 생성 스크립트 (GPU 최적화 - 범용)
# 수정사항: 임베딩 순환 참조 방지, max_length=2048 설정

set -e  # 오류 발생 시 중단

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 현재 디렉토리를 프로젝트 루트로 사용
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

echo "===================================="
echo "ClassMate Embedding Generation"
echo "GPU Optimized (Auto-detect)"
echo "===================================="
echo ""
echo "작업 디렉토리: ${SCRIPT_DIR}"

# GPU 확인
if command -v nvidia-smi &> /dev/null; then
    echo ""
    echo -e "${GREEN}GPU 상태:${NC}"
    nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv
    echo ""
    GPU_BATCH=16
    GPU_INTERVAL=150
else
    echo -e "${YELLOW}⚠ GPU 없음 - CPU 모드${NC}"
    GPU_BATCH=4
    GPU_INTERVAL=50
fi

# 가상환경 자동 감지
VENV_FOUND=false

for VENV_NAME in "venv_classmate" "venv" ".venv" "env"; do
    if [ -d "${VENV_NAME}" ]; then
        echo -e "${GREEN}✓ 가상환경 발견: ${VENV_NAME}${NC}"
        source "${VENV_NAME}/bin/activate"
        VENV_FOUND=true
        break
    fi
done

if [ "$VENV_FOUND" = false ]; then
    echo -e "${YELLOW}⚠ 가상환경을 찾을 수 없습니다${NC}"
    echo "  다음 중 하나를 생성하세요: venv_classmate, venv, .venv"
    read -p "가상환경 없이 계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Neo4j 연결 확인
echo ""
echo -e "${YELLOW}Neo4j 연결 확인 중...${NC}"
python3 -c "
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

try:
    driver = GraphDatabase.driver(
        os.getenv('NEO4J_URI', 'neo4j://localhost:7687'),
        auth=(os.getenv('NEO4J_USERNAME', 'neo4j'),
              os.getenv('NEO4J_PASSWORD', 'password'))
    )
    driver.verify_connectivity()
    driver.close()
    print('✓ Neo4j 연결 성공')
except Exception as e:
    print(f'✗ Neo4j 연결 실패: {e}')
    exit(1)
" || exit 1

echo ""
echo "===================================="
echo "임베딩 생성 시작"
echo "Batch size: ${GPU_BATCH}"
echo "GPU clear interval: ${GPU_INTERVAL}"
echo "===================================="
echo ""

# 로그 파일명
LOG_FILE="embedding_$(date +%Y%m%d_%H%M%S).log"
echo "로그 파일: ${LOG_FILE}"
echo ""

# 임베딩 실행
python3 embedding.py \
    --batch ${GPU_BATCH} \
    --gpu-clear-interval ${GPU_INTERVAL} \
    --rel-summary 0 \
    --log-level INFO \
    2>&1 | tee "${LOG_FILE}"

# 결과 확인
RESULT=$?

echo ""
echo "===================================="
if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ 임베딩 생성 완료!${NC}"
else
    echo -e "${RED}✗ 오류 발생 (exit code: ${RESULT})${NC}"
    echo "  로그 확인: ${LOG_FILE}"
fi
echo "===================================="

# GPU 최종 상태
if command -v nvidia-smi &> /dev/null; then
    echo ""
    echo "GPU 최종 상태:"
    nvidia-smi --query-gpu=name,memory.used,memory.free --format=csv
fi

exit $RESULT
