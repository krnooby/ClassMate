#!/bin/bash
# React Frontend 개발 서버 실행 스크립트

echo "🎨 Starting ClassMate Frontend..."
echo "   URL: http://localhost:5173"
echo ""
echo "⚠️  백엔드 API 서버가 실행 중이어야 합니다!"
echo "   (다른 터미널에서 ./run_api_server.sh 실행)"
echo ""

cd "$(dirname "$0")"
npm run dev
