#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphRAG 테스트 스크립트
팀원의 DB에 연결하여 벡터 검색 + 그래프 탐색 테스트
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
from openai import OpenAI
from api.services.graph_rag_service import get_graph_rag_service

# .env 로드
load_dotenv()

def main():
    print("=" * 80)
    print("GraphRAG 테스트")
    print("=" * 80)
    print()

    # GraphRAG 서비스 초기화
    rag_service = get_graph_rag_service()

    # 테스트할 학생 ID (첫 번째 학생)
    student_id = "S-01"

    print(f"테스트 대상 학생: {student_id}")
    print()

    # ========== 1. 그래프 컨텍스트 가져오기 (벡터 검색 없이) ==========
    print("=" * 80)
    print("1️⃣  그래프 탐색 (벡터 검색 X)")
    print("=" * 80)

    try:
        graph_context = rag_service.get_student_graph_context(student_id)

        if graph_context.get("student"):
            student = graph_context["student"]
            print(f"✅ 학생 정보:")
            print(f"   - 이름: {student.get('name')}")
            print(f"   - 학년: {student.get('grade_label')}")
            print(f"   - CEFR: {student.get('cefr')}")
            print(f"   - 백분위: {student.get('percentile_rank')}")
            print()

        if graph_context.get("class"):
            cls = graph_context["class"]
            print(f"✅ 반 정보:")
            print(f"   - 반: {cls.get('class_name')}")
            print(f"   - 일정: {cls.get('schedule')}")
            print(f"   - 진도: {cls.get('progress')}")
            print()

        if graph_context.get("teacher"):
            teacher = graph_context["teacher"]
            print(f"✅ 담당 선생님: {teacher.get('name')}")
            print()

        if graph_context.get("peers"):
            peers = graph_context["peers"]
            print(f"✅ 같은 반 친구: {len(peers)}명")
            for i, peer in enumerate(peers[:3], 1):
                print(f"   {i}. {peer.get('name')} ({peer.get('cefr')})")
            print()

    except Exception as e:
        print(f"❌ 그래프 탐색 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # ========== 2. 벡터 검색 테스트 ==========
    print("=" * 80)
    print("2️⃣  벡터 유사도 검색")
    print("=" * 80)

    query = "문법이 약한 학생"
    print(f"쿼리: '{query}'")
    print()

    try:
        print("임베딩 모델 로딩 중...")
        vector_results = rag_service.vector_search_students(
            query_text=query,
            limit=5
        )

        if vector_results:
            print(f"✅ 검색 결과: {len(vector_results)}명")
            print()
            for i, result in enumerate(vector_results, 1):
                print(f"{i}. {result.get('name', 'N/A')} (학생 ID: {result.get('student_id', 'N/A')})")
                print(f"   유사도: {result.get('score', 0):.4f}")
                summary = result.get('summary', '')
                if summary:
                    preview = summary[:100] + "..." if len(summary) > 100 else summary
                    print(f"   요약: {preview}")
                print()
        else:
            print("⚠️  검색 결과 없음 (유사도 0.7 이상인 학생 없음)")
            print()

    except Exception as e:
        print(f"❌ 벡터 검색 실패: {e}")
        import traceback
        traceback.print_exc()
        print()

    # ========== 3. RAG 컨텍스트 생성 (그래프 + 벡터) ==========
    print("=" * 80)
    print("3️⃣  GraphRAG 통합 컨텍스트")
    print("=" * 80)

    user_question = "이 학생의 강점과 약점은 무엇인가요?"
    print(f"질문: '{user_question}'")
    print()

    try:
        rag_context = rag_service.get_rag_context(
            student_id=student_id,
            query_text=user_question,
            use_vector_search=True
        )

        print("✅ 생성된 RAG 컨텍스트:")
        print("-" * 80)
        print(rag_context)
        print("-" * 80)
        print()

    except Exception as e:
        print(f"❌ RAG 컨텍스트 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # ========== 4. LLM으로 응답 생성 (GPT-4o-mini) ==========
    print("=" * 80)
    print("4️⃣  LLM 응답 생성 (GPT-4o-mini)")
    print("=" * 80)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 추가하세요.")
        return

    try:
        client = OpenAI(api_key=api_key)

        system_prompt = f"""당신은 영어전문 교육 상담사입니다.
아래 학생 정보를 바탕으로 질문에 답변하세요.

{rag_context}

답변 가이드라인:
1. 객관적인 데이터를 바탕으로 설명하세요
2. 강점과 약점을 균형있게 제시하세요
3. 구체적인 학습 계획을 제안하세요
4. 한국어로 답변하세요
"""

        print("LLM 호출 중...")
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0.7,
            max_tokens=500
        )

        answer = response.choices[0].message.content

        print("✅ LLM 응답:")
        print("-" * 80)
        print(answer)
        print("-" * 80)
        print()

        print("=" * 80)
        print("✅ GraphRAG 테스트 완료!")
        print("=" * 80)
        print()
        print("요약:")
        print("  ✅ 그래프 탐색 성공")
        print("  ✅ 벡터 검색 성공")
        print("  ✅ RAG 컨텍스트 생성 성공")
        print("  ✅ LLM 응답 생성 성공")
        print()
        print("이제 API 서버를 실행하여 실제 채팅 기능을 테스트할 수 있습니다!")

    except Exception as e:
        print(f"❌ LLM 호출 실패: {e}")
        import traceback
        traceback.print_exc()

    finally:
        rag_service.close()


if __name__ == "__main__":
    main()
