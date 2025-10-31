# -*- coding: utf-8 -*-
"""
Parent Agent Service
OpenAI Function Calling 기반 학부모 상담 시스템
"""
from __future__ import annotations
import os
import json
import re
import random
from typing import List, Dict, Any, Optional
from openai import OpenAI
from shared.services import (
    get_graph_rag_service,
    get_dictionary_service,
    get_news_service,
    get_text_analysis_service,
    get_grammar_check_service
)
from shared.services.youtube_service import get_youtube_service
from shared.prompts import PromptManager
from shared.services.tts_service import get_tts_service


# ANSI 색상 코드
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # 색상
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # 배경색
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


def print_box(title: str, content: str, color: str = Colors.CYAN):
    """박스 형태로 로그 출력"""
    width = 80
    print(f"\n{color}{'='*width}{Colors.RESET}")
    print(f"{color}{Colors.BOLD}{title.center(width)}{Colors.RESET}")
    print(f"{color}{'='*width}{Colors.RESET}")
    for line in content.split('\n'):
        if line.strip():
            print(f"{color}  {line}{Colors.RESET}")
    print(f"{color}{'='*width}{Colors.RESET}\n")


def print_section(emoji: str, title: str, content: str, color: str = Colors.BLUE):
    """섹션 형태로 로그 출력"""
    print(f"\n{color}{Colors.BOLD}{emoji} {title}{Colors.RESET}")
    print(f"{color}{'-'*60}{Colors.RESET}")
    for line in content.split('\n'):
        if line.strip():
            print(f"{color}  {line}{Colors.RESET}")
    print()


class ParentAgentService:
    """학부모 맞춤 Function Calling 에이전트"""

    def __init__(self):
        """초기화"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key)
        self.graph_rag_service = get_graph_rag_service()

        # Current user message for vector search context
        self.current_user_message = ""

        # Current session ID for audio tracking
        self.current_session_id = None

        # Function definitions
        self.functions = self._create_functions()

    def _route_query(self, message: str, student_id: str) -> str:
        """
        질문 의도를 분석하여 적절한 모델 선택
        Returns: "intelligence" (gpt-4.1-mini) or "reasoning" (o4-mini/o3)
        """
        routing_prompt = f'''Analyze this parent's question and choose the appropriate model:

**intelligence** (gpt-4.1-mini) - Fast, cost-effective for:
- Simple information lookup (성적 조회, 출석 확인, 기본 정보)
- Direct questions with single answer (몇 점?, 누가?, 언제?)
- Greetings and small talk (안녕하세요, 잘 지내?)
- Function calls only (DB 조회만 필요)
- Basic status requests
Examples: "우리 아이 성적이 어때?", "출석률은?", "강점이 뭐야?", "최근 푼 문제는?", "안녕하세요"

**reasoning** (o4-mini) - Deep thinking for:
- Multi-step analysis (여러 단계 분석 필요)
- Comparative reasoning (비교 분석, 트렌드 파악)
- Strategic planning (학습 계획, 개선 방안 수립)
- Cause-effect relationships (원인 분석 → 해결책)
- Synthesis of multiple data points (종합적 판단)
Examples: "약점을 분석하고 4주 계획 세워줘", "다른 아이들과 비교해서 어떤 부분을 개선해야 할까?", "왜 성적이 떨어졌고 어떻게 해야 할까?", "듣기와 문법 중 뭘 먼저 공부해야 할까?"

Question: "{message}"

Respond with ONLY "intelligence" or "reasoning".'''

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cheap, fast router
                messages=[{"role": "user", "content": routing_prompt}],
                max_tokens=10,
                temperature=0
            )
            decision = response.choices[0].message.content.strip().lower()

            # 시각적 로깅
            if decision == "intelligence":
                print_section(
                    "🧠",
                    "ROUTING DECISION",
                    f"Query: {message[:50]}...\n"
                    f"Model: INTELLIGENCE (gpt-4.1-mini)\n"
                    f"Reason: Fast function calling for simple tasks",
                    Colors.CYAN
                )
            else:
                print_section(
                    "🧠",
                    "ROUTING DECISION",
                    f"Query: {message[:50]}...\n"
                    f"Model: REASONING (o4-mini)\n"
                    f"Reason: Deep thinking required for complex analysis",
                    Colors.MAGENTA
                )

            return decision if decision in ["intelligence", "reasoning"] else "intelligence"
        except Exception as e:
            print(f"{Colors.RED}⚠️  Routing failed: {e}, defaulting to intelligence{Colors.RESET}")
            return "intelligence"  # Default fallback

    def _check_response_quality(self, response_text: str) -> bool:
        """
        Check if o4-mini response quality is acceptable
        Returns: True if good, False if needs o3 fallback
        """
        # Bad indicators: too short, generic, error patterns
        if len(response_text) < 50:
            return False
        if "죄송합니다" in response_text and "오류" in response_text:
            return False
        if response_text.count("...") > 3:  # Too many ellipses = incomplete
            return False
        return True

    def _needs_react(self, message: str) -> bool:
        """
        ReAct 모드가 필요한 복잡한 질문인지 판단

        복잡한 질문 패턴:
        1. 연결어가 있는 다단계 작업: "~하고 ~해줘", "~찾아서 ~해줘"
        2. 순차적 지시: "먼저 ~ 그다음 ~"
        3. 동사 3개 이상 (여러 작업)
        """
        import re

        # 패턴 1: 연결어 ("하고", "찾아서", "확인하고" 등)
        multi_task_keywords = ['하고', '그리고', '찾아서', '확인하고', '조회하고', '알려주고', '분석하고', '추천해']
        for keyword in multi_task_keywords:
            if keyword in message and ('해줘' in message or '주세요' in message or '줘' in message):
                return True

        # 패턴 2: "먼저...그다음" 또는 "먼저...그리고"
        if '먼저' in message and ('그다음' in message or '그리고' in message):
            return True

        # 패턴 3: 동사 3개 이상
        action_verbs = ['찾', '분석', '추천', '확인', '조회', '검색', '비교', '생성', '설명', '알려', '보여', '세워']
        verb_count = sum(1 for verb in action_verbs if verb in message)
        if verb_count >= 3:
            return True

        return False

    def _react_chat(
        self,
        student_id: str,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_steps: int = 5
    ) -> Dict[str, Any]:
        """
        ReAct (Reasoning + Acting) 모드로 복잡한 다단계 작업 처리

        Args:
            student_id: 학생 ID (학부모의 자녀)
            message: 학부모의 메시지
            chat_history: 이전 대화 기록
            max_steps: 최대 반복 횟수

        Returns:
            Dict with 'message' and 'model_info'
        """
        print(f"\n{'='*60}")
        print(f"🔄 ReAct Mode Activated (Parent)")
        print(f"Query: {message}")
        print(f"{'='*60}\n")

        # System prompt
        system_prompt = PromptManager.get_system_prompt(
            role="parent",
            model="o4-mini",
            context={"student_id": student_id}
        )

        # 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]

        if chat_history:
            messages.extend(chat_history)

        messages.append({"role": "user", "content": message})

        used_models = ["gpt-4o-mini (router)", "o4-mini (ReAct)"]

        # ReAct 루프
        for step in range(1, max_steps + 1):
            print(f"\n--- ReAct Step {step}/{max_steps} ---")

            # LLM 호출
            response = self.client.chat.completions.create(
                model="o4-mini",
                messages=messages,
                tools=self.functions,
                tool_choice="auto",
                max_completion_tokens=10000
            )

            assistant_message = response.choices[0].message

            # Thought 출력 (LLM의 사고 과정)
            if assistant_message.content:
                print(f"💭 Thought: {assistant_message.content[:200]}...")

            # Function 호출이 있으면 실행
            if assistant_message.tool_calls:
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    print(f"🔧 Action: {function_name}({arguments})")

                    # Function 실행
                    result = self._execute_function(function_name, arguments)

                    print(f"📊 Observation: {result[:200]}...")

                    # Observation을 메시지에 추가
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                # Final answer (Function 호출 없음)
                print(f"✅ Final Answer Reached")

                content = assistant_message.content or "답변을 생성할 수 없습니다."

                # Quick reply 파싱
                parsed = self._parse_quick_reply(content, used_models)

                return parsed

        # 최대 반복 횟수 초과
        print(f"⚠️  Max steps ({max_steps}) reached")

        # 마지막 응답 생성
        final_response = self.client.chat.completions.create(
            model="o4-mini",
            messages=messages,
            max_completion_tokens=10000
        )

        content = final_response.choices[0].message.content or "최대 반복 횟수를 초과했습니다. 질문을 더 구체적으로 해주세요."

        parsed = self._parse_quick_reply(content, used_models)

        return parsed

    def _create_functions(self) -> List[Dict[str, Any]]:
        """OpenAI Function Calling용 function 정의"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_child_info",
                    "description": "자녀의 상세 학습 정보를 조회합니다 (이름, 학년, CEFR 레벨, 강점, 약점, 영역별 점수, 출석률, 숙제 완료율, 학습 태도, 반 정보 등)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID (예: S-01)"
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_performance",
                    "description": "자녀의 성적 분석 및 학습 추이를 조회합니다 (영역별 강약점, 또래 비교, 개선 추이)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID"
                            },
                            "focus_area": {
                                "type": "string",
                                "description": "집중 분석할 영역 (독해, 문법, 어휘, 듣기, 쓰기 중 하나, 또는 null일 경우 전체 분석)",
                                "enum": ["독해", "문법", "어휘", "듣기", "쓰기", None]
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_study_advice",
                    "description": "자녀의 약점을 보완하기 위한 맞춤형 학습 조언 및 가정 학습 가이드를 제공합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID"
                            },
                            "area": {
                                "type": "string",
                                "description": "조언이 필요한 영역 (독해, 문법, 어휘, 듣기, 쓰기 중 하나, 또는 null일 경우 전체 약점 기반)",
                                "enum": ["독해", "문법", "어휘", "듣기", "쓰기", None]
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_attendance_status",
                    "description": "자녀의 출석 현황, 숙제 완료율, 학습 태도 등 일일 학습 기록을 조회합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID"
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recommend_improvement_areas",
                    "description": "자녀가 집중적으로 개선해야 할 영역과 구체적인 학습 계획을 추천합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID"
                            },
                            "priority": {
                                "type": "string",
                                "description": "우선순위 기준 (urgent: 시급한 약점, balanced: 균형 잡힌 학습, strength: 강점 강화)",
                                "enum": ["urgent", "balanced", "strength"]
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_problem",
                    "description": "AI가 새로운 영어 문제를 생성합니다 (고품질). 듣기 문제는 자동으로 대화 음성과 [AUDIO], [SPEAKERS] 태그가 포함됩니다. difficulty를 생략하면 학생의 CEFR 레벨에 맞춰 자동 생성됩니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "학생 ID (CEFR 레벨 자동 조회용)"
                            },
                            "area": {
                                "type": "string",
                                "description": "문제 영역: '듣기' (listening), '독해' (reading), '문법' (grammar), '어휘' (vocabulary), '쓰기' (writing)"
                            },
                            "difficulty": {
                                "type": "string",
                                "description": "난이도 CEFR 레벨 (A1, A2, B1, B2, C1, C2). 생략 시 학생의 현재 레벨 사용"
                            },
                            "topic": {
                                "type": "string",
                                "description": "주제 - 사용자가 언급한 주제를 사용하세요. 예: 여행, 쇼핑, 레스토랑 예약, 병원 예약, 도서관, 영화관, 운동, 취미, 학교 생활, 친구 모임, 가족 행사, 휴가 계획, 봉사활동 등. 언급이 없으면 다양한 주제 중 하나를 선택하세요."
                            },
                            "num_speakers": {
                                "type": "integer",
                                "description": "듣기 문제의 화자 수 (2, 3, 4 등). 사용자가 '3명', '여러 명', '세 명' 등을 언급하면 해당 숫자를 사용하세요. 기본값은 2명입니다."
                            }
                        },
                        "required": ["student_id", "area"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "lookup_word",
                    "description": "영어 단어를 검색하여 발음, 정의, 예문, 동의어를 제공합니다 (자녀 학습 지원용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "word": {
                                "type": "string",
                                "description": "검색할 영어 단어 (예: confident, beautiful, education)"
                            }
                        },
                        "required": ["word"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_news",
                    "description": "영어 학습용 최신 뉴스 기사를 가져옵니다 (자녀와 함께 읽을 수 있는 영어 뉴스)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "뉴스 카테고리: general(일반), sports(스포츠), technology(기술), health(건강), science(과학), entertainment(엔터)",
                                "enum": ["general", "sports", "technology", "health", "science", "entertainment"],
                                "default": "general"
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "가져올 기사 수 (1-10, 기본값 3)",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_text_difficulty",
                    "description": "영어 텍스트의 난이도(CEFR 레벨)와 가독성을 분석합니다 (자녀가 읽는 글의 수준 파악용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "분석할 영어 텍스트 (최소 1문장 이상)"
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_grammar",
                    "description": "영어 문장의 문법 오류를 자동으로 검사하고 수정 제안을 제공합니다 (자녀 학습 지원용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "검사할 영어 문장 또는 단락"
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_youtube",
                    "description": "자녀의 영어 학습에 도움되는 YouTube 영상/채널을 검색합니다. CEFR 레벨과 관심 주제에 맞춰 교육용 콘텐츠를 추천합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "학생 ID (CEFR 레벨 자동 조회용)"
                            },
                            "search_type": {
                                "type": "string",
                                "description": "검색 타입: 'video' (영상 검색) 또는 'channel' (채널 검색)",
                                "enum": ["video", "channel"],
                                "default": "video"
                            },
                            "topic": {
                                "type": "string",
                                "description": "검색 주제 (예: 'English listening practice', 'kids vocabulary', 'phonics songs'). 학생의 CEFR 레벨과 흥미를 고려하세요."
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "반환할 최대 결과 수 (1-10, 기본값 5)",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["student_id", "topic"]
                    }
                }
            }
        ]

    def _get_child_info(self, student_id: str, query_text: str = "학생 정보 조회") -> str:
        """자녀 정보 조회 실행 (벡터 검색 포함)"""
        try:
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query_text,
                use_vector_search=True
            )

            # 학부모 관점에서 정보 재구성
            if context:
                import re
                # 이름 추출
                name_match = re.search(r'이름: (.+)', context)
                student_name = name_match.group(1) if name_match else "자녀"

                # CEFR 레벨 추출
                cefr_match = re.search(r'CEFR 레벨: ([A-C][1-2])', context)
                cefr_level = cefr_match.group(1) if cefr_match else "N/A"

                return f"""**{student_name} 학생의 학습 현황 (학부모님 관점):**

{context}

**학부모님께 안내 사항:**
- 현재 자녀의 CEFR 레벨은 {cefr_level}입니다
- 정기적인 출석과 숙제 완료가 성적 향상에 중요합니다
- 가정에서도 꾸준한 학습 습관 형성이 필요합니다
"""
            return context
        except Exception as e:
            return f"자녀 정보 조회 실패: {str(e)}"

    def _analyze_performance(self, student_id: str, focus_area: Optional[str] = None) -> str:
        """성적 분석 실행"""
        try:
            # GraphRAG를 통해 성적 정보 조회
            query = f"자녀의 {focus_area} 성적 분석" if focus_area else "자녀의 전체 성적 분석 및 또래 비교"
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query,
                use_vector_search=True
            )

            # 성적 분석 리포트 생성
            analysis = f"""**성적 분석 리포트**

{context}

**또래 비교 분석:**
- 같은 반 학생들과 비교하여 상위권/중위권/하위권 파악
- 영역별 강약점 분석

**개선 추이:**
- 최근 학습 활동 기록을 바탕으로 성장 가능성 예측
- 꾸준한 학습이 필요한 영역 식별
"""
            return analysis

        except Exception as e:
            return f"성적 분석 실패: {str(e)}"

    def _get_study_advice(self, student_id: str, area: Optional[str] = None) -> str:
        """학습 조언 제공"""
        try:
            # GraphRAG를 통해 약점 영역 파악
            query = f"{area} 영역 개선 방안" if area else "전체 약점 개선 방안"
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query,
                use_vector_search=True
            )

            # 모델 선택: 특정 영역 조언은 간단 → gpt-4.1-mini, 전체 영역은 추론 필요 → o4-mini
            model = "gpt-4.1-mini" if area else "o4-mini"
            print(f"📊 학습 조언 생성 모델: {model}")

            # 학습 조언 생성
            advice_prompt = f"""당신은 교육 전문가입니다. 다음 학생 정보를 바탕으로 학부모님께 맞춤형 학습 조언을 제공해주세요.

**학생 정보:**
{context}

**조언 영역:**
{area if area else "전체 영역"}

**다음 형식으로 답변해주세요:**

1. **현재 상황 요약**
   - 자녀의 강점과 약점 간략히 정리

2. **가정에서 도와주실 수 있는 방법**
   - 구체적이고 실천 가능한 3-5가지 방법
   - 매일 또는 매주 할 수 있는 활동

3. **추천 학습 자료**
   - 영어 학습 앱, 책, 웹사이트 등

4. **학습 시간 및 환경 관리**
   - 효과적인 학습 시간대
   - 집중력을 높이는 환경 조성법

존댓말을 사용하고, 실천 가능한 조언을 제공해주세요.
"""

            # 모델에 따라 적절한 파라미터 사용
            if model == "o4-mini":
                response = self.client.chat.completions.create(
                    model="o4-mini",
                    messages=[
                        {"role": "system", "content": "당신은 학부모 상담 전문 교육 컨설턴트입니다."},
                        {"role": "user", "content": advice_prompt}
                    ],
                    max_completion_tokens=3000
                )
            else:
                response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "당신은 학부모 상담 전문 교육 컨설턴트입니다."},
                        {"role": "user", "content": advice_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )

            return response.choices[0].message.content

        except Exception as e:
            return f"학습 조언 생성 실패: {str(e)}"

    def _get_attendance_status(self, student_id: str) -> str:
        """출석 및 숙제 현황 조회"""
        try:
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text="출석률, 숙제 완료율, 학습 태도",
                use_vector_search=False  # 직접 그래프 조회
            )

            return f"""**출석 및 학습 태도 현황**

{context}

**학부모님께 안내:**
- 정기적인 출석이 학습 성과에 가장 중요한 요소입니다
- 숙제는 수업 내용 복습 및 이해도 확인을 위해 필수적입니다
- 학습 태도는 장기적인 영어 실력 향상의 핵심입니다
"""
        except Exception as e:
            return f"출석 현황 조회 실패: {str(e)}"

    def _recommend_improvement_areas(self, student_id: str, priority: str = "urgent") -> str:
        """개선 영역 추천"""
        try:
            # 우선순위 기준에 따라 쿼리 조정
            if priority == "urgent":
                query = "가장 시급하게 개선이 필요한 약점 영역"
            elif priority == "balanced":
                query = "균형 잡힌 학습을 위한 전체 영역 개선 계획"
            else:  # strength
                query = "강점을 더욱 강화하기 위한 심화 학습 방안"

            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query,
                use_vector_search=True
            )

            # 모델 선택: 4주 학습 계획 같은 복잡한 추론 → o4-mini
            model = "o4-mini"
            print(f"📊 개선 계획 생성 모델: {model}")

            # 개선 계획 생성
            plan_prompt = f"""당신은 교육 전문가입니다. 다음 학생 정보를 바탕으로 학부모님께 구체적인 개선 계획을 제시해주세요.

**학생 정보:**
{context}

**우선순위:**
{priority} ({'시급한 약점 개선' if priority == 'urgent' else '균형 잡힌 학습' if priority == 'balanced' else '강점 강화'})

**다음 형식으로 답변해주세요:**

1. **우선 개선 영역 (1-2개)**
   - 영역명과 현재 수준
   - 개선이 필요한 이유

2. **4주 학습 계획**
   - 주차별 학습 목표
   - 구체적인 학습 활동 (매일 10-15분)

3. **중간 점검 방법**
   - 2주 후 확인할 사항
   - 개선 여부 판단 기준

4. **학원과 가정의 역할**
   - 학원에서 제공하는 것
   - 가정에서 도와주실 것

존댓말을 사용하고, 실천 가능한 계획을 제공해주세요.
"""

            response = self.client.chat.completions.create(
                model="o4-mini",
                messages=[
                    {"role": "system", "content": "당신은 학부모 상담 전문 교육 컨설턴트입니다."},
                    {"role": "user", "content": plan_prompt}
                ],
                max_completion_tokens=3000
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"개선 계획 생성 실패: {str(e)}"

    def _generate_problem(self, student_id: str, area: str, difficulty: str = None, topic: str = None, num_speakers: int = 2) -> str:
        """AI 문제 생성 실행 (o4-mini - 빠른 추론 모델)"""
        try:
            # topic이 없으면 다양한 주제 중 랜덤 선택
            if not topic:
                topics = [
                    "레스토랑 예약", "영화관 방문", "도서관 이용", "쇼핑", "병원 예약",
                    "여행 계획", "운동", "취미 활동", "학교 생활", "친구 모임",
                    "가족 행사", "휴가 계획", "봉사활동", "동아리 활동", "파티 준비"
                ]
                topic = random.choice(topics)
                print(f"📌 자동 선택된 주제: {topic}")

            # difficulty가 지정되지 않았으면 학생의 CEFR 레벨 조회
            if not difficulty:
                try:
                    # GraphRAG 서비스를 통해 학생 정보 조회
                    student_context = self.graph_rag_service.get_rag_context(
                        student_id=student_id,
                        query_text="학생의 CEFR 레벨 알려줘",
                        use_vector_search=False  # 직접 그래프 조회
                    )

                    # CEFR 레벨 추출 (A1, A2, B1, B2, C1, C2 중 하나)
                    cefr_match = re.search(r'\b(A1|A2|B1|B2|C1|C2)\b', student_context, re.IGNORECASE)
                    if cefr_match:
                        difficulty = cefr_match.group(1).upper()
                        print(f"📊 학생 {student_id}의 CEFR 레벨: {difficulty}")
                    else:
                        # 기본값: B1
                        difficulty = "B1"
                        print(f"⚠️  학생 {student_id}의 CEFR 레벨을 찾을 수 없어 기본값 B1 사용")
                except Exception as e:
                    print(f"⚠️  CEFR 레벨 조회 실패: {e}, 기본값 B1 사용")
                    difficulty = "B1"

            # PromptManager를 사용해 문제 생성 프롬프트 가져오기
            prompt = PromptManager.get_problem_generation_prompt(
                area=area,
                difficulty=difficulty,
                topic=topic,
                num_speakers=num_speakers,
                model="o4-mini"
            )

            is_listening = area.lower() in ['듣기', 'listening', 'ls']
            print(f"🎯 문제 생성: area={area}, difficulty={difficulty}, topic={topic}, num_speakers={num_speakers}, is_listening={is_listening}")

            # 듣기 문제는 최대 2회 재시도
            max_attempts = 2 if is_listening else 1

            for attempt in range(max_attempts):
                try:
                    # o4-mini - o3-mini 후속, 빠른 속도 + 우수한 STEM 성능
                    # NOTE: o4-mini uses reasoning tokens + output tokens, so we need more tokens for listening problems
                    max_tokens = 10000 if is_listening else 3000
                    response = self.client.chat.completions.create(
                        model="o4-mini",
                        messages=[{"role": "user", "content": prompt}],
                        max_completion_tokens=max_tokens
                    )

                    content = response.choices[0].message.content

                    if is_listening and content:
                        print(f"✅ o4-mini 듣기 문제 생성 완료: {len(content)} 글자")

                    # 듣기 문제 후처리
                    if is_listening:
                        content = self._postprocess_listening_problem(content, attempt + 1)
                        # 학부모용 지도 가이드 추가
                        content = self._add_parent_guidance(content, difficulty, topic)

                    return content

                except Exception as retry_error:
                    if attempt == max_attempts - 1:
                        raise retry_error
                    print(f"⚠️  듣기 문제 생성 재시도 ({attempt + 1}/{max_attempts})")
                    continue

        except Exception as e:
            # Fallback to GPT-4o (빠르고 안정적)
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an expert English language teacher creating high-quality assessment questions."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    max_tokens=1500
                )

                content = response.choices[0].message.content

                # 듣기 문제 후처리
                if is_listening:
                    content = self._postprocess_listening_problem(content, attempt=1)
                    # 학부모용 지도 가이드 추가
                    content = self._add_parent_guidance(content, difficulty, topic)

                return content

            except Exception as fallback_error:
                return f"문제 생성 실패: {str(e)}, Fallback 실패: {str(fallback_error)}"

    def _postprocess_listening_problem(self, content: str, attempt: int) -> str:
        """
        듣기 문제 후처리 (강제 검증 및 수정)

        1. 한글 텍스트 제거 (TTS에서 읽히지 않도록)
        2. [AUDIO]: 패턴 확인 및 추가
        3. [SPEAKERS]: JSON 파싱 및 자동 생성
        4. 대화 형식 검증
        5. 첫 발화에 화자 이름 추가
        """
        # ========================================
        # STEP 1: 한글 텍스트 제거 (TTS 음성 방지)
        # ========================================
        # 1. 괄호 안의 한글 번역 제거 (예: "(안녕, 파티에 올 거야?)" → "")
        # 2. 완전히 한글로만 된 설명 줄만 제거
        # 3. 영어 대화는 유지

        korean_char_pattern = re.compile(r'[\u3131-\u3163\uac00-\ud7a3]')  # 한글 유니코드 범위

        cleaned_lines = []
        for line in content.split('\n'):
            # 괄호 안의 한글 번역 제거 (예: "Hello! (안녕!) How are you? (어떻게 지내?)" → "Hello! How are you?")
            cleaned_line = re.sub(r'\([^)]*[\u3131-\u3163\uac00-\ud7a3][^)]*\)', '', line)
            # 연속된 공백을 단일 공백으로 정리
            cleaned_line = re.sub(r'\s+', ' ', cleaned_line).strip()

            # 완전히 한글로만 된 줄만 제거 (설명 줄)
            # 예: "음성 링크를 클릭하여 듣기 연습", "[음성 내용 요약]", "- 공원 청소 봉사 활동이..."
            if re.match(r'^[\s\u3131-\u3163\uac00-\ud7a3\[\]:\-•※\(\)]+$', cleaned_line):
                print(f"   🗑️  한글 설명 줄 제거: {line[:50]}...")
                continue

            # 빈 줄은 유지 (구조 보존)
            cleaned_lines.append(cleaned_line if cleaned_line else line)

        content = '\n'.join(cleaned_lines)
        print(f"   ✅ 한글 텍스트 제거 완료 (대화 스크립트 유지)")

        lines = content.split('\n')

        # 1. [AUDIO]: 패턴 확인
        has_audio_tag = any('[AUDIO]:' in line for line in lines)

        # 2. [SPEAKERS]: JSON 파싱
        speakers_match = re.search(r'\[SPEAKERS\]:\s*({.*})', content)
        has_speakers_tag = speakers_match is not None

        # Check if voice field exists in existing SPEAKERS JSON
        needs_voice_enhancement = False
        if has_speakers_tag:
            try:
                existing_speakers = json.loads(speakers_match.group(1))
                speakers_list = existing_speakers.get('speakers', [])
                # Check if ANY speaker is missing voice field
                if speakers_list and not all('voice' in s for s in speakers_list):
                    needs_voice_enhancement = True
                    print(f"   ⚠️  [SPEAKERS]: voice 필드 없음 → o4-mini로 추가 예정")
            except:
                pass

        # 3. 대화 형식 확인 (Name: text 패턴)
        dialogue_pattern = re.compile(r'^([A-Z][a-z]+):\s+.+', re.MULTILINE)
        dialogue_matches = dialogue_pattern.findall(content)

        # 첫 번째 대화 찾기 (화자 없이 시작하는 경우도 포함)
        # 예: "Hi Jake, have you done..." 같은 경우
        first_utterance_pattern = re.compile(r'^[A-Z][^:]{10,}', re.MULTILINE)
        first_utterance_matches = first_utterance_pattern.findall(content)

        has_dialogue = len(dialogue_matches) >= 1 or len(first_utterance_matches) >= 1

        print(f"🔍 듣기 문제 검증 (시도 {attempt}):")
        print(f"   - [AUDIO]: {has_audio_tag}")
        print(f"   - [SPEAKERS]: {has_speakers_tag}")
        print(f"   - 대화 형식 (Name:): {len(dialogue_matches)}개")
        print(f"   - 첫 발화 (화자 없음): {len(first_utterance_matches)}개")

        # 대화 형식이 없으면 독백형으로 간주 (화자 분리 없음)
        if not has_dialogue:
            print(f"   ℹ️  독백형 듣기 문제 (화자 분리 없음)")
            print(f"   ✅ 듣기 문제 검증 통과 (독백형)!")
            return '\n'.join(lines)  # 후처리 없이 그대로 반환

        # [AUDIO]: 태그 강제 추가
        if not has_audio_tag:
            print(f"   ⚠️  [AUDIO]: 태그 없음 → 강제 추가")
            # Find first dialogue line or first utterance
            first_dialogue_idx = None
            for i, line in enumerate(lines):
                if dialogue_pattern.match(line.strip()) or first_utterance_pattern.match(line.strip()):
                    first_dialogue_idx = i
                    break

            if first_dialogue_idx is not None:
                lines.insert(first_dialogue_idx, '[AUDIO]:')

        # [SPEAKERS]: JSON 자동 생성 또는 voice enhancement
        if (not has_speakers_tag or needs_voice_enhancement) and has_dialogue:
            if not has_speakers_tag:
                print(f"   ⚠️  [SPEAKERS]: 태그 없음 → 자동 생성")
            else:
                print(f"   ⚠️  [SPEAKERS]: voice 필드 추가 중...")

            # Extract unique speaker names from existing labels
            unique_speakers = []
            seen = set()
            for match in dialogue_matches:
                if match not in seen:
                    unique_speakers.append(match)
                    seen.add(match)

            # If only 1 speaker found but we need 2, add a default second speaker
            if len(unique_speakers) == 1:
                # Infer second speaker from context
                first_name = unique_speakers[0]
                # Default second names
                if first_name.lower() in ['emma', 'sarah', 'lisa', 'maria', 'anna']:
                    second_name = 'Jake'  # Male counterpart
                else:
                    second_name = 'Emma'  # Female counterpart
                unique_speakers.insert(0, second_name)  # Add as first speaker
                print(f"   ℹ️  화자 1명만 감지 → 두 번째 화자 추가: {second_name}")

            # Use LLM to determine gender and voice for each speaker
            # Build a prompt for the LLM
            speaker_names = ", ".join(unique_speakers)
            llm_prompt = f"""Given these speaker names: {speaker_names}

For EACH speaker, determine:
1. Gender (male or female)
2. US English voice name - IMPORTANT: Assign DIFFERENT voices to DIFFERENT speakers!

Available voices:
- Female voices: Samantha, Karen, Victoria
- Male voices: David, Daniel, Mark

CRITICAL RULES:
- If you have 2 speakers, they MUST use DIFFERENT voice names
- Never assign the same voice to multiple speakers in one conversation
- Example (CORRECT): Speaker1 uses Samantha, Speaker2 uses David
- Example (WRONG): Speaker1 uses Samantha, Speaker2 uses Samantha

Respond with ONLY valid JSON:
{{
  "speakers": [
    {{"name": "Name1", "gender": "female", "voice": "Samantha"}},
    {{"name": "Name2", "gender": "male", "voice": "David"}}
  ]
}}"""

            try:
                # Call LLM to determine speakers (o4-mini - 추론 모델)
                llm_response = self.client.chat.completions.create(
                    model="o4-mini",  # Reasoning model for speaker analysis
                    messages=[{"role": "user", "content": llm_prompt}],
                    max_completion_tokens=300
                )

                # o4-mini doesn't support JSON mode, parse from text
                content_llm = llm_response.choices[0].message.content
                # Extract JSON from response (handle markdown code blocks)
                json_match = re.search(r'\{.*\}', content_llm, re.DOTALL)
                if json_match:
                    speakers_json = json.loads(json_match.group(0))
                else:
                    speakers_json = json.loads(content_llm)

                print(f"   ✅ o4-mini가 화자 정보 생성: {speakers_json}")

            except Exception as e:
                print(f"   ⚠️  LLM 호출 실패, fallback to rules: {e}")
                # Fallback to rule-based
                female_names = {'sarah', 'emma', 'lisa', 'maria', 'anna', 'kate', 'jane', 'mary', 'lucy', 'emily'}
                male_names = {'tom', 'john', 'mike', 'david', 'james', 'robert', 'mark', 'peter', 'kevin', 'alex', 'jake'}

                speakers_json = {"speakers": []}
                for name in unique_speakers:
                    name_lower = name.lower()
                    if name_lower in female_names:
                        gender = "female"
                        voice = "Samantha"
                    elif name_lower in male_names:
                        gender = "male"
                        voice = "David"
                    else:
                        # Default: alternate male/female
                        gender = "female" if len(speakers_json["speakers"]) % 2 == 0 else "male"
                        voice = "Samantha" if gender == "female" else "David"

                    speakers_json["speakers"].append({"name": name, "gender": gender, "voice": voice})

            # Insert or Replace [SPEAKERS]: line
            speakers_line = f"[SPEAKERS]: {json.dumps(speakers_json)}"

            if needs_voice_enhancement:
                # Replace existing [SPEAKERS]: line
                for i, line in enumerate(lines):
                    if '[SPEAKERS]:' in line:
                        lines[i] = speakers_line
                        print(f"   ✅ [SPEAKERS]: voice 필드 추가 완료 ({len(speakers_json['speakers'])}명)")
                        break
            else:
                # Insert new [SPEAKERS]: line after [AUDIO]:
                audio_idx = None
                for i, line in enumerate(lines):
                    if '[AUDIO]:' in line:
                        audio_idx = i
                        break

                if audio_idx is not None:
                    lines.insert(audio_idx + 1, speakers_line)
                    print(f"   ✅ [SPEAKERS]: 자동 생성 완료 ({len(speakers_json['speakers'])}명)")

        # 4. 첫 발화에 화자 이름 추가 (없는 경우)
        # Re-parse speakers JSON to get first speaker
        speakers_match = re.search(r'\[SPEAKERS\]:\s*({.*})', '\n'.join(lines))
        if speakers_match:
            try:
                speakers_data = json.loads(speakers_match.group(1))
                speakers_list = speakers_data.get('speakers', [])

                if speakers_list:
                    first_speaker = speakers_list[0]['name']

                    # Find first line after [SPEAKERS]: that looks like dialogue but has no speaker label
                    speakers_idx = None
                    for i, line in enumerate(lines):
                        if '[SPEAKERS]:' in line:
                            speakers_idx = i
                            break

                    if speakers_idx is not None:
                        # Check next few lines for dialogue without speaker
                        for i in range(speakers_idx + 1, min(speakers_idx + 5, len(lines))):
                            line = lines[i].strip()
                            # Skip empty lines and lines that already have speaker labels
                            if not line or dialogue_pattern.match(line):
                                continue
                            # If it's a sentence (starts with capital, has words)
                            if re.match(r'^[A-Z][^:]{10,}', line):
                                # Add first speaker name
                                lines[i] = f"{first_speaker}: {line}"
                                print(f"   ✅ 첫 발화에 화자 추가: {first_speaker}:")
                                break
            except Exception as e:
                print(f"   ⚠️  첫 발화 화자 추가 실패: {e}")

        result = '\n'.join(lines)

        # Final verification
        final_has_audio = '[AUDIO]:' in result
        final_has_speakers = '[SPEAKERS]:' in result
        final_dialogue_count = len(re.findall(r'^([A-Z][a-z]+):\s+', result, re.MULTILINE))

        print(f"   📊 최종 대화 수: {final_dialogue_count}개")

        if final_has_audio and final_has_speakers and final_dialogue_count >= 2:
            print(f"   ✅ 듣기 문제 검증 통과!")
        else:
            print(f"   ⚠️  최종 검증 - AUDIO: {final_has_audio}, SPEAKERS: {final_has_speakers}, 대화: {final_dialogue_count}개")

        # 🎙️ OpenAI TTS로 고품질 음성 생성
        if final_has_audio and final_has_speakers:
            try:
                print(f"   🎙️  OpenAI TTS 음성 생성 중...")
                tts_service = get_tts_service()
                audio_url = tts_service.get_or_create_audio(result, session_id=self.current_session_id)

                if audio_url:
                    # Add audio URL to the beginning of the problem (for frontend to use)
                    result = f"[AUDIO_URL]: {audio_url}\n\n{result}"
                    print(f"   ✅ TTS 음성 생성 완료: {audio_url}")
                else:
                    print(f"   ⚠️  TTS 음성 생성 실패 - 브라우저 TTS 사용")
            except Exception as e:
                print(f"   ⚠️  TTS 오디오 생성 오류: {e}")
                print(f"   ℹ️  브라우저 TTS fallback 사용")

        return result

    def _add_parent_guidance(self, problem_content: str, difficulty: str, topic: str) -> str:
        """
        듣기 문제에 학부모 지도 가이드 추가

        Args:
            problem_content: 생성된 듣기 문제
            difficulty: CEFR 레벨
            topic: 주제

        Returns:
            문제 + 학부모 지도 가이드
        """
        try:
            print(f"   📚 학부모 지도 가이드 생성 중...")

            # 문제에서 대화 스크립트 추출 (간단하게 [AUDIO]: 이후 부분)
            import re
            audio_match = re.search(r'\[AUDIO\]:(.+?)(?:\n\n|\n(?=[A-Z])|\Z)', problem_content, re.DOTALL)
            dialogue_sample = audio_match.group(1).strip()[:300] if audio_match else ""

            guidance_prompt = f"""당신은 영어 교육 전문가이자 학부모 상담사입니다.

다음 듣기 문제를 자녀와 함께 학습할 때, 학부모님이 어떻게 지도하면 좋을지 **실천 가능한 구체적인 가이드**를 작성해주세요.

**듣기 문제 정보:**
- CEFR 레벨: {difficulty}
- 주제: {topic}
- 대화 예시: {dialogue_sample[:200]}...

**학부모 지도 가이드 작성 형식:**

---

## 📚 학부모님을 위한 지도 가이드

### 1️⃣ 듣기 전 준비 (Pre-listening)
- 자녀에게 주제({topic})에 대해 먼저 이야기 나누기
  예: "오늘은 {topic}에 관한 대화를 들을 거야. 너는 {topic}에 대해 어떻게 생각해?"
- 주요 단어 2-3개를 미리 설명 (필요시)

### 2️⃣ 듣기 중 활동 (While-listening)
- 첫 번째 듣기: 전체 내용 파악 (정답 맞히기보다 이해하기)
- 두 번째 듣기: 문제 풀면서 듣기
- **TIP**: 자녀가 어려워하면 자막(스크립트)을 함께 보면서 들어도 OK!

### 3️⃣ 듣기 후 활동 (Post-listening)
- 정답 확인 및 왜 그런지 함께 생각해보기
- 대화 스크립트를 천천히 읽어보며 모르는 단어 찾기
- 자녀와 역할 놀이로 대화 따라 읽기 (발음 연습)

### 4️⃣ 가정에서 할 수 있는 활동 (5-10분)
- 비슷한 상황 역할극 (자녀와 함께 연기하기)
- 대화의 한 부분을 우리말로 바꿔 말하기
- "{topic}" 관련 영어 단어 3개 더 찾아보기

### 5️⃣ 학부모님께 당부 말씀
- 정답을 못 맞혀도 괜찮습니다. 영어를 듣고 이해하는 과정 자체가 중요해요.
- 자녀가 영어로 대답하지 못해도 한글로 설명하면 이해한 것입니다.
- 매일 5분씩 꾸준히 하는 것이 하루 30분 몰아서 하는 것보다 효과적입니다.

---

위 형식으로 이 듣기 문제에 맞는 **구체적이고 실천 가능한** 가이드를 작성해주세요.
존댓말을 사용하고, 학부모님이 바로 따라 할 수 있도록 예시를 포함해주세요."""

            # 모델 선택: 실천 가능한 간단한 가이드 → gpt-4.1-mini
            model = "gpt-4.1-mini"
            print(f"📊 학부모 지도 가이드 생성 모델: {model}")

            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "당신은 영어 교육 전문가이자 학부모 상담사입니다."},
                    {"role": "user", "content": guidance_prompt}
                ],
                temperature=0.7,
                max_tokens=1200
            )

            guidance = response.choices[0].message.content

            # 문제 + 지도 가이드 결합
            result = f"{problem_content}\n\n{guidance}"

            print(f"   ✅ 학부모 지도 가이드 추가 완료")
            return result

        except Exception as e:
            print(f"   ⚠️  지도 가이드 생성 실패: {e}, 문제만 반환")
            return problem_content  # 실패 시 문제만 반환

    def _parse_quick_reply(self, content: str, used_models: List[str]) -> Dict[str, Any]:
        """
        응답에서 [QUICK_REPLY:...] 패턴을 파싱하여 quick_replies 필드로 변환

        Format: [QUICK_REPLY:VO|RD|WR|LS|GR]
        각 코드는 클릭 가능한 버튼으로 변환됨
        """
        import re

        # Quick reply 패턴 검색
        pattern = r'\[QUICK_REPLY:(.*?)\]'
        match = re.search(pattern, content)

        if match:
            # Quick reply 코드 추출 (예: "VO|RD|WR|LS|GR")
            codes = match.group(1).split('|')

            # 코드를 한글 이름과 매핑
            code_mapping = {
                "VO": {"label": "어휘 (Vocabulary)", "value": "어휘 문제 내줘"},
                "RD": {"label": "독해 (Reading)", "value": "독해 문제 내줘"},
                "WR": {"label": "쓰기 (Writing)", "value": "쓰기 문제 내줘"},
                "LS": {"label": "듣기 (Listening)", "value": "듣기 문제 내줘"},
                "GR": {"label": "문법 (Grammar)", "value": "문법 문제 내줘"}
            }

            # Quick replies 생성
            quick_replies = []
            for code in codes:
                code = code.strip()
                if code in code_mapping:
                    quick_replies.append(code_mapping[code])

            # 패턴 제거한 메시지
            clean_message = re.sub(pattern, '', content).strip()

            return {
                "message": clean_message,
                "quick_replies": quick_replies,
                "model_info": {
                    "primary": "o4-mini (ReAct)" if "ReAct" in str(used_models) else "gpt-4.1-mini",
                    "all_used": used_models
                }
            }
        else:
            # Quick reply 없으면 일반 응답
            return {
                "message": content,
                "model_info": {
                    "primary": "o4-mini (ReAct)" if "ReAct" in str(used_models) else "gpt-4.1-mini",
                    "all_used": used_models
                }
            }

    def _lookup_word(self, word: str) -> str:
        """영어 단어 검색 (Free Dictionary API)"""
        try:
            service = get_dictionary_service()
            result = service.lookup_word(word)

            if not result.get('success'):
                return f"단어 '{word}'를 찾을 수 없습니다. 철자를 확인해주세요."

            # 결과를 사용자 친화적으로 포맷팅
            response = f"**{result['word']}** {result.get('phonetic', '')}\n\n"
            response += f"**품사:** {result.get('part_of_speech', 'N/A')}\n\n"
            response += f"**정의:** {result.get('definition', 'N/A')}\n\n"

            if result.get('example'):
                response += f"**예문:** {result['example']}\n\n"

            if result.get('synonyms'):
                synonyms = ', '.join(result['synonyms'])
                response += f"**동의어:** {synonyms}\n\n"

            if result.get('antonyms'):
                antonyms = ', '.join(result['antonyms'])
                response += f"**반의어:** {antonyms}\n\n"

            # 발음 오디오 URL이 있으면 추가
            phonetics = result.get('phonetics', [])
            audio_urls = [p['audio'] for p in phonetics if p.get('audio')]
            if audio_urls:
                response += f"**발음 듣기:** {audio_urls[0]}\n"

            return response
        except Exception as e:
            return f"단어 검색 실패: {str(e)}"

    def _fetch_news(self, category: str = "general", page_size: int = 3) -> str:
        """영어 뉴스 기사 검색 (NewsAPI)"""
        try:
            service = get_news_service()
            result = service.fetch_news(
                category=category,
                language="en",
                page_size=min(page_size, 5),  # 최대 5개
                country="us"
            )

            if not result.get('success'):
                error_msg = result.get('error', 'Unknown error')
                if "NEWS_API_KEY not configured" in error_msg:
                    return "뉴스 API가 설정되지 않았습니다. 관리자에게 문의하세요."
                return f"뉴스 검색 실패: {error_msg}"

            articles = result.get('articles', [])
            if not articles:
                return f"'{category}' 카테고리의 뉴스를 찾을 수 없습니다."

            # 기사 포맷팅
            response = f"**{category.title()} 카테고리 최신 뉴스** ({len(articles)}개)\n\n"

            for i, article in enumerate(articles, 1):
                response += f"**{i}. {article['title']}**\n"
                response += f"   *출처:* {article['source']}\n"
                if article.get('description'):
                    response += f"   *요약:* {article['description']}\n"
                response += f"   *링크:* {article['url']}\n\n"

            return response
        except Exception as e:
            return f"뉴스 검색 실패: {str(e)}"

    def _analyze_text_difficulty(self, text: str) -> str:
        """텍스트 난이도 분석 (textstat)"""
        try:
            service = get_text_analysis_service()
            result = service.analyze_cefr_level(text)

            if not result.get('success'):
                error_msg = result.get('error', 'Unknown error')
                if "textstat library not installed" in error_msg:
                    return "텍스트 분석 라이브러리가 설치되지 않았습니다. 관리자에게 문의하세요."
                return f"텍스트 분석 실패: {error_msg}"

            # 결과 포맷팅
            response = f"**텍스트 난이도 분석 결과**\n\n"
            response += f"**CEFR 레벨:** {result['cefr_level']}\n"
            response += f"**난이도:** {result['difficulty']}\n"
            response += f"**가독성 점수 (Flesch):** {result['flesch_reading_ease']}/100 (높을수록 쉬움)\n"
            response += f"**학년 수준 (FK Grade):** {result['flesch_kincaid_grade']}학년\n\n"
            response += f"**통계:**\n"
            response += f"- 단어 수: {result['word_count']}개\n"
            response += f"- 문장 수: {result['sentence_count']}개\n"
            response += f"- 평균 문장 길이: {result['avg_sentence_length']}단어\n\n"

            # 레벨별 설명
            level_descriptions = {
                "A1": "초급 - 매우 쉬운 텍스트",
                "A2": "초급 상 - 쉬운 텍스트",
                "B1": "중급 - 보통 난이도 텍스트",
                "B2": "중급 상 - 어려운 텍스트",
                "C1": "고급 - 매우 어려운 텍스트",
                "C2": "고급 상 - 전문가 수준 텍스트"
            }
            response += f"**레벨 설명:** {level_descriptions.get(result['cefr_level'], 'N/A')}\n"

            return response
        except Exception as e:
            return f"텍스트 분석 실패: {str(e)}"

    def _check_grammar(self, text: str) -> str:
        """문법 검사 (LanguageTool API)"""
        try:
            service = get_grammar_check_service()
            result = service.check_grammar(text, language="en-US")

            if not result.get('success'):
                return f"문법 검사 실패: {result.get('error', 'Unknown error')}"

            error_count = result.get('error_count', 0)
            errors = result.get('errors', [])

            if error_count == 0:
                return "**문법 검사 결과:** 문법 오류가 없습니다! 잘했어요! ✅"

            # 오류 포맷팅
            response = f"**문법 검사 결과:** {error_count}개의 오류 발견\n\n"

            for i, error in enumerate(errors[:10], 1):  # 최대 10개만 표시
                response += f"**{i}. {error['message']}**\n"

                # 오류 위치 표시
                offset = error['offset']
                length = error['length']
                error_text = text[offset:offset+length]
                response += f"   *문제:* \"{error_text}\"\n"

                # 수정 제안
                replacements = error.get('replacements', [])
                if replacements:
                    suggestions = ', '.join([f'"{r}"' for r in replacements])
                    response += f"   *제안:* {suggestions}\n"

                # 카테고리
                category = error.get('category', '')
                if category:
                    response += f"   *유형:* {category}\n"

                response += "\n"

            if error_count > 10:
                response += f"*({error_count - 10}개 오류 더 있음)*\n"

            return response
        except Exception as e:
            return f"문법 검사 실패: {str(e)}"

    def _search_youtube(
        self,
        student_id: str,
        topic: str,
        search_type: str = "video",
        max_results: int = 5
    ) -> str:
        """YouTube 영상/채널 검색 (자녀 학습용)"""
        try:
            # 학생 CEFR 레벨 조회
            student_info = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text="CEFR 레벨",
                use_vector_search=False
            )

            cefr_level = "A1"  # 기본값
            if student_info:
                import re
                cefr_match = re.search(r'CEFR 레벨: ([A-C][1-2])', student_info)
                if cefr_match:
                    cefr_level = cefr_match.group(1)

            # 검색 쿼리 최적화 (CEFR 레벨 + 주제)
            optimized_query = f"English {topic} {cefr_level} level for kids education"

            print(f"🎥 YouTube Search: {optimized_query} (type: {search_type})")

            youtube_service = get_youtube_service()

            if search_type == "channel":
                results = youtube_service.search_channels(
                    query=optimized_query,
                    max_results=max_results
                )
            else:
                results = youtube_service.search_videos(
                    query=optimized_query,
                    max_results=max_results,
                    video_duration="medium"  # 4-20분 영상
                )

            if not results:
                return f"죄송합니다. '{topic}' 관련 YouTube {search_type}을(를) 찾을 수 없습니다. 다른 주제로 시도해보세요."

            # 결과 포맷팅
            if search_type == "channel":
                response = f"**🎬 '{topic}' 관련 YouTube 채널 추천 (CEFR {cefr_level} 레벨):**\n\n"
                for i, channel in enumerate(results, 1):
                    response += f"**{i}. {channel['title']}**\n"
                    response += f"   📺 채널: {channel['url']}\n"
                    if channel['description']:
                        desc = channel['description'][:100] + "..." if len(channel['description']) > 100 else channel['description']
                        response += f"   📝 {desc}\n"
                    response += "\n"
            else:
                response = f"**🎬 '{topic}' 관련 YouTube 영상 추천 (CEFR {cefr_level} 레벨):**\n\n"
                for i, video in enumerate(results, 1):
                    response += f"**{i}. {video['title']}**\n"
                    response += f"   📺 채널: {video['channel']}\n"
                    response += f"   🔗 링크: {video['url']}\n"
                    if video['description']:
                        desc = video['description'][:100] + "..." if len(video['description']) > 100 else video['description']
                        response += f"   📝 {desc}\n"
                    response += "\n"

            response += "\n💡 **가정 학습 팁:**\n"
            response += "• 자녀와 함께 영상을 시청하세요\n"
            response += "• 영상을 본 후 간단한 질문으로 이해도를 확인하세요\n"
            response += "• 하루 10-15분 정도가 적당합니다\n"

            return response

        except Exception as e:
            return f"YouTube 검색 실패: {str(e)}\n\n직접 YouTube에서 '{topic}'으로 검색해보세요."

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Function 실행"""

        # 함수 타입 분류
        db_functions = ["get_child_info", "analyze_performance", "get_attendance_status"]
        generation_functions = ["get_study_advice", "recommend_improvement_areas", "generate_problem"]
        external_api_functions = ["lookup_word", "fetch_news", "analyze_text_difficulty", "check_grammar", "search_youtube"]

        if function_name in db_functions:
            func_type = "📊 DATABASE QUERY"
            color = Colors.GREEN
        elif function_name in generation_functions:
            func_type = "🤖 AI GENERATION"
            color = Colors.MAGENTA
        elif function_name in external_api_functions:
            func_type = "🌐 EXTERNAL API"
            color = Colors.BLUE
        else:
            func_type = "❓ UNKNOWN"
            color = Colors.RED

        print_section(
            "🔧",
            f"FUNCTION CALL - {func_type}",
            f"Function: {function_name}\n"
            f"Arguments: {json.dumps(arguments, ensure_ascii=False, indent=2)}",
            color
        )

        if function_name == "get_child_info":
            # 벡터 검색을 위해 현재 사용자 메시지 전달
            result = self._get_child_info(query_text=self.current_user_message, **arguments)
        elif function_name == "analyze_performance":
            result = self._analyze_performance(**arguments)
        elif function_name == "get_study_advice":
            result = self._get_study_advice(**arguments)
        elif function_name == "get_attendance_status":
            result = self._get_attendance_status(**arguments)
        elif function_name == "recommend_improvement_areas":
            result = self._recommend_improvement_areas(**arguments)
        elif function_name == "generate_problem":
            result = self._generate_problem(**arguments)
        elif function_name == "lookup_word":
            result = self._lookup_word(**arguments)
        elif function_name == "fetch_news":
            result = self._fetch_news(**arguments)
        elif function_name == "analyze_text_difficulty":
            result = self._analyze_text_difficulty(**arguments)
        elif function_name == "check_grammar":
            result = self._check_grammar(**arguments)
        elif function_name == "search_youtube":
            result = self._search_youtube(**arguments)
        else:
            result = f"Unknown function: {function_name}"

        # 결과 미리보기 출력
        result_preview = result[:200] + "..." if len(result) > 200 else result
        print(f"{Colors.GREEN}✅ Function completed: {result_preview}{Colors.RESET}\n")

        return result

    def chat(
        self,
        student_id: str,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        학부모와 채팅 (Function Calling)

        Args:
            student_id: 자녀의 학생 ID
            message: 학부모의 메시지
            chat_history: 이전 대화 기록 (선택)
            session_id: 세션 ID (오디오 추적용, 선택)

        Returns:
            Dict with 'message' and 'model_info'
        """
        try:
            # ========== 요청 시작 로깅 ==========
            print_box(
                "👪 PARENT CHATBOT REQUEST",
                f"Child ID: {student_id}\n"
                f"Message: {message}\n"
                f"Session ID: {session_id or 'None'}",
                Colors.MAGENTA
            )

            # 현재 사용자 메시지 저장 (벡터 검색용)
            self.current_user_message = message

            # 현재 세션 ID 저장 (오디오 추적용)
            self.current_session_id = session_id

            # ReAct 모드 판단 (복잡한 다단계 질문)
            if self._needs_react(message):
                return self._react_chat(student_id, message, chat_history)

            # "문제 내줘" 패턴 감지 (유형 미지정)
            import re
            if re.search(r'(?:문제|problem)\s*(?:내|줘|풀|해)', message, re.IGNORECASE) and \
               not re.search(r'(?:듣기|독해|문법|어휘|쓰기|listening|reading|grammar|vocabulary|writing|VO|RD|GR|LS|WR)', message, re.IGNORECASE):
                # 유형이 명시되지 않은 일반적인 "문제 내줘" 요청
                print("🔍 문제 유형 선택 요청 감지 (학부모)")
                return {
                    "message": "자녀를 위해 어떤 유형의 문제를 준비해드릴까요?",
                    "quick_replies": [
                        {"label": "💬 듣기 (Listening)", "value": "듣기 문제 내줘"},
                        {"label": "📖 독해 (Reading)", "value": "독해 문제 내줘"},
                        {"label": "✍️ 쓰기 (Writing)", "value": "쓰기 문제 내줘"},
                        {"label": "📝 문법 (Grammar)", "value": "문법 문제 내줘"},
                        {"label": "📚 어휘 (Vocabulary)", "value": "어휘 문제 내줘"}
                    ],
                    "model_info": {
                        "primary": "gpt-4.1-mini",
                        "all_used": ["gpt-4.1-mini"]
                    }
                }

            used_models = []  # Track models used

            # Step 1: Route the query to determine complexity
            routing_decision = self._route_query(message, student_id)
            used_models.append("gpt-4o-mini")  # Router model

            # Step 2: Select primary model based on routing decision
            if routing_decision == "reasoning":
                primary_model = "o4-mini"
                print(f"🎯 Using reasoning model: {primary_model}")
            else:
                primary_model = "gpt-4.1-mini"
                print(f"🎯 Using intelligence model: {primary_model}")

            # PromptManager를 사용해 시스템 프롬프트 생성
            system_prompt = PromptManager.get_system_prompt(
                role="parent",
                model=primary_model,
                context={"student_id": student_id}
            )

            # 메시지 구성 (멀티턴 지원)
            messages = [{"role": "system", "content": system_prompt}]

            # 대화 히스토리 추가
            if chat_history:
                print(f"💬 Multi-turn enabled: {len(chat_history)} previous messages")
                messages.extend(chat_history)
            else:
                print(f"💬 Single-turn conversation (no history)")

            # 최신 사용자 메시지 추가
            messages.append({"role": "user", "content": message})
            print(f"📝 Total messages sent to LLM: {len(messages)}")

            # Step 3: Call primary model with function calling
            used_models.append(primary_model)

            # Use appropriate parameters based on model type
            if primary_model == "o4-mini":
                # o4-mini uses max_completion_tokens
                response = self.client.chat.completions.create(
                    model="o4-mini",
                    messages=messages,
                    tools=self.functions,
                    tool_choice="auto",
                    max_completion_tokens=10000
                )
            else:
                # gpt-4.1-mini uses max_tokens
                response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    tools=self.functions,
                    tool_choice="auto",
                    temperature=0.7
                )

            assistant_message = response.choices[0].message

            # Function 호출이 있는 경우
            if assistant_message.tool_calls:
                # Function 실행
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    print(f"🔧 Function Call: {function_name}({arguments})")

                    # Track special models used in functions
                    if function_name in ["get_study_advice", "recommend_improvement_areas"]:
                        used_models.append("gpt-4o")
                    elif function_name == "generate_problem":
                        used_models.append("o4-mini")

                    # Function 실행
                    function_response = self._execute_function(function_name, arguments)

                    # 듣기 문제의 경우: [AUDIO]와 [SPEAKERS] 태그를 보존하기 위해 직접 반환
                    if function_name == "generate_problem" and arguments.get("area", "").lower() in ['듣기', 'listening', 'ls']:
                        # Check if response contains [AUDIO] or [SPEAKERS]
                        if '[AUDIO]' in function_response or '[SPEAKERS]' in function_response:
                            print("🎧 듣기 문제: [AUDIO]/[SPEAKERS] 태그 보존을 위해 직접 반환")
                            return {
                                "message": function_response,
                                "model_info": {
                                    "primary": "o4-mini",
                                    "all_used": list(set(used_models))
                                }
                            }

                    # Function 결과를 메시지에 추가
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    })

                # Function 결과를 바탕으로 최종 응답 생성
                # Use the same model as primary for consistency
                if primary_model == "o4-mini":
                    final_response = self.client.chat.completions.create(
                        model="o4-mini",
                        messages=messages,
                        max_completion_tokens=10000
                    )
                else:
                    final_response = self.client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=messages,
                        temperature=0.7
                    )

                response_content = final_response.choices[0].message.content

                # Step 4: Quality check for o4-mini responses
                if primary_model == "o4-mini" and not self._check_response_quality(response_content):
                    print(f"⚠️  o4-mini response quality low, falling back to o3...")
                    used_models.append("o3")

                    # Retry with o3 (advanced reasoning)
                    try:
                        final_response_o3 = self.client.chat.completions.create(
                            model="o3",
                            messages=messages,
                            max_completion_tokens=10000
                        )
                        response_content = final_response_o3.choices[0].message.content
                        primary_model = "o3"  # Update primary model
                        print(f"✅ o3 response generated successfully")
                    except Exception as e:
                        print(f"⚠️  o3 fallback failed: {e}, using o4-mini response anyway")

                return {
                    "message": response_content,
                    "model_info": {
                        "primary": primary_model,
                        "all_used": list(set(used_models))
                    }
                }
            else:
                # Function 호출 없이 직접 응답
                response_content = assistant_message.content

                # Step 4: Quality check for o4-mini responses (no function calls)
                if primary_model == "o4-mini" and not self._check_response_quality(response_content):
                    print(f"⚠️  o4-mini response quality low, falling back to o3...")
                    used_models.append("o3")

                    # Retry with o3 (advanced reasoning)
                    try:
                        final_response_o3 = self.client.chat.completions.create(
                            model="o3",
                            messages=messages,
                            max_completion_tokens=10000
                        )
                        response_content = final_response_o3.choices[0].message.content
                        primary_model = "o3"  # Update primary model
                        print(f"✅ o3 response generated successfully")
                    except Exception as e:
                        print(f"⚠️  o3 fallback failed: {e}, using o4-mini response anyway")

                return {
                    "message": response_content,
                    "model_info": {
                        "primary": primary_model,
                        "all_used": list(set(used_models))
                    }
                }

        except Exception as e:
            return {
                "message": f"죄송합니다. 오류가 발생했습니다: {str(e)}",
                "model_info": {"primary": "error", "all_used": []}
            }


# 싱글톤 인스턴스
_parent_agent_service = None


def get_parent_agent_service() -> ParentAgentService:
    """Parent Agent 서비스 싱글톤 인스턴스 가져오기"""
    global _parent_agent_service
    if _parent_agent_service is None:
        _parent_agent_service = ParentAgentService()
    return _parent_agent_service
