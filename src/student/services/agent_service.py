# -*- coding: utf-8 -*-
"""
Student Agent Service
OpenAI Function Calling 기반 학생 상담 시스템
"""
from __future__ import annotations
import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from shared.services import (
    get_graph_rag_service,
    get_dictionary_service,
    get_news_service,
    get_text_analysis_service,
    get_grammar_check_service
)
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


class StudentAgentService:
    """학생 맞춤 Function Calling 에이전트"""

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
        routing_prompt = f'''Analyze this student's question and choose the appropriate model:

**intelligence** (gpt-4.1-mini) - Fast, cost-effective for:
- Simple problem requests (문제 내줘, 듣기 문제, 독해 문제)
- Greetings and casual chat (안녕?, 잘 지내?, 고마워)
- Basic function calls (점수 보기, 힌트 달라)
- Quick answers (정답이 뭐야?, 몇 점이야?)
- Encouragement and simple feedback
Examples: "문제 내줘", "듣기 문제 풀게", "안녕?", "힌트 줘", "정답 알려줘", "고마워"

**reasoning** (o4-mini) - Deep thinking for:
- In-depth explanations (문법 개념 설명, 왜 그런지)
- Complex grammar concepts (가정법, 관계대명사 심화)
- Multi-step problem solving (여러 단계 풀이)
- Learning strategy advice (어떻게 공부해야 할까?)
- Analysis of mistakes (왜 틀렸는지 분석)
Examples: "왜 이 답이 틀렸어?", "가정법 과거완료를 자세히 설명해줘", "독해 실력을 늘리려면 어떻게 해야 돼?", "이 문제 풀이 과정을 단계별로 보여줘", "be동사와 일반동사의 차이를 깊게 알려줘"

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
                    f"Reason: Deep thinking required for complex explanation",
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
        """ReAct 모드가 필요한 복잡한 질문인지 판단"""
        import re

        reasons = []

        # 패턴 1: 연결어 ("하고", "찾아서")
        multi_task_keywords = ['하고', '그리고', '찾아서', '확인하고', '조회하고', '알려주고']
        for keyword in multi_task_keywords:
            if keyword in message and ('해줘' in message or '주세요' in message or '줘' in message):
                reasons.append(f"Multi-task keyword detected: '{keyword}'")

        # 패턴 2: "먼저...그다음"
        if '먼저' in message and ('그다음' in message or '그리고' in message):
            reasons.append("Sequential task pattern: '먼저...그다음'")

        # 패턴 3: 동사 3개 이상
        action_verbs = ['찾', '분석', '추천', '확인', '조회', '검색', '비교', '생성', '설명', '알려']
        verb_count = sum(1 for verb in action_verbs if verb in message)
        if verb_count >= 3:
            reasons.append(f"Multiple action verbs: {verb_count} detected")

        needs_react = len(reasons) > 0

        if needs_react:
            print_section(
                "🔄",
                "ReAct MODE ACTIVATED",
                f"Query: {message}\n" + "\n".join(f"- {r}" for r in reasons),
                Colors.YELLOW
            )

        return needs_react

    def _react_chat(
        self,
        student_id: str,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_steps: int = 5
    ) -> Dict[str, Any]:
        """ReAct (Reasoning + Acting) 모드로 복잡한 다단계 작업 처리"""

        print(f"\n{'='*60}")
        print(f"🔄 ReAct Mode Activated")
        print(f"Query: {message}")
        print(f"{'='*60}\n")

        # System prompt
        system_prompt = PromptManager.get_system_prompt(
            role="student_agent",
            model="o4-mini",
            context={"student_id": student_id}
        )

        # 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)

        # 초기 user 메시지
        messages.append({"role": "user", "content": message})

        used_models = ["o4-mini (ReAct)"]

        for step in range(1, max_steps + 1):
            print(f"\n--- ReAct Step {step}/{max_steps} ---")

            # LLM 호출 (o4-mini)
            response = self.client.chat.completions.create(
                model="o4-mini",
                messages=messages,
                tools=self.functions,
                tool_choice="auto",
                max_completion_tokens=10000
            )

            assistant_message = response.choices[0].message

            # Thought 출력
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

                    # Tool result 추가
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                # Final answer
                print(f"✅ Final Answer Reached")

                content = assistant_message.content or "답변을 생성할 수 없습니다."

                # Quick reply 파싱
                parsed = self._parse_quick_reply(content, used_models)

                return parsed

        # 최대 단계 도달 - 마지막 응답 요청
        print(f"⚠️  Max steps reached, generating final answer...")

        messages.append({
            "role": "user",
            "content": "Based on the information you've gathered, provide your final answer."
        })

        final_response = self.client.chat.completions.create(
            model="o4-mini",
            messages=messages,
            max_completion_tokens=10000
        )

        content = final_response.choices[0].message.content or "답변을 생성할 수 없습니다."
        parsed = self._parse_quick_reply(content, used_models)

        return parsed

    def _create_functions(self) -> List[Dict[str, Any]]:
        """OpenAI Function Calling용 function 정의"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_student_context",
                    "description": "학생의 상세 정보를 조회합니다 (이름, 학년, CEFR 레벨, 강점, 약점, 영역별 점수, 출석률, 숙제 완료율, 반 정보, 시간표 등)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "학생 ID (예: S-01)"
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recommend_problems",
                    "description": "DB에서 학생의 약점에 맞는 영어 문제를 추천합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "학생 ID"
                            },
                            "area": {
                                "type": "string",
                                "description": "문제 영역 (독해, 문법, 어휘, 듣기, 쓰기 중 하나, 또는 null일 경우 약점 자동 감지)",
                                "enum": ["독해", "문법", "어휘", "듣기", "쓰기", None]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "문제 개수 (기본값 3)",
                                "default": 3
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
                    "name": "evaluate_writing",
                    "description": "쓰기(서술형) 답안을 AI가 종합적으로 평가합니다 (문법, 어휘, 구조, 내용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "쓰기 문제 프롬프트 (주제/질문)"
                            },
                            "student_answer": {
                                "type": "string",
                                "description": "학생이 작성한 영어 답안"
                            },
                            "difficulty": {
                                "type": "string",
                                "description": "난이도 CEFR 레벨 (A1, A2, B1, B2, C1, C2)"
                            }
                        },
                        "required": ["prompt", "student_answer", "difficulty"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "lookup_word",
                    "description": "영어 단어를 검색하여 발음, 정의, 예문, 동의어를 제공합니다 (Free Dictionary API, 무료)",
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
                    "description": "영어 학습용 최신 뉴스 기사를 가져옵니다 (NewsAPI). 뉴스를 읽고 싶거나, 최신 주제로 학습하고 싶을 때 사용하세요.",
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
                    "description": "영어 텍스트의 난이도(CEFR 레벨)와 가독성을 분석합니다. 학생이 작성한 글이나 읽은 지문의 수준을 파악할 때 사용하세요.",
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
                    "description": "영어 문장의 문법 오류를 자동으로 검사하고 수정 제안을 제공합니다 (LanguageTool API, 무료). 학생이 작성한 문장을 검토할 때 사용하세요.",
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
            }
        ]

    def _get_student_context(self, student_id: str, query_text: str = "학생 정보 조회") -> str:
        """학생 정보 조회 실행 (벡터 검색 포함)"""
        try:
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query_text,
                use_vector_search=True
            )
            return context
        except Exception as e:
            return f"학생 정보 조회 실패: {str(e)}"

    def _recommend_problems(self, student_id: str, area: Optional[str] = None, limit: int = 3) -> str:
        """문제 추천 실행"""
        try:
            # Writing(서술형)은 DB에서 추천하지 않음 - 항상 generate_problem 사용
            if area and area.upper() in ['WR', 'WRITING', '쓰기']:
                return "쓰기(Writing) 문제는 DB 추천이 불가능합니다. generate_problem function을 사용하여 자유 서술형 문제를 생성해주세요."

            problems = self.graph_rag_service.search_problems_for_student(
                student_id=student_id,
                area=area,
                limit=limit
            )

            if not problems:
                return "해당 조건에 맞는 문제를 찾을 수 없습니다."

            # 문제를 텍스트로 변환
            result = []
            area_names = {
                'RD': 'Reading', 'GR': 'Grammar', 'WR': 'Writing',
                'LS': 'Listening', 'VO': 'Vocabulary'
            }

            for i, p in enumerate(problems, 1):
                area_en = area_names.get(p['area'], p['area'])
                problem_text = f"Problem {i} [{area_en}]:\n"

                # Listening 문제는 audio_transcript 포함
                if p.get('audio_transcript'):
                    problem_text += f"[AUDIO]: {p['audio_transcript']}\n"

                # Figure (그림) 포함
                if p.get('figures'):
                    for fig in p['figures']:
                        if fig.get('public_url'):
                            problem_text += f"[IMAGE]: {fig['public_url']}\n"
                            if fig.get('caption'):
                                problem_text += f"  Caption: {fig['caption']}\n"

                # Table (표) 포함
                if p.get('tables'):
                    for tbl in p['tables']:
                        if tbl.get('public_url'):
                            problem_text += f"[TABLE]: {tbl['public_url']}\n"
                            if tbl.get('title'):
                                problem_text += f"  Title: {tbl['title']}\n"

                problem_text += f"{p['stem']}\n"
                if p['options']:
                    for j, opt in enumerate(p['options'], 1):
                        problem_text += f"   {j}) {opt}\n"
                problem_text += f"Answer: {p['answer']}\n"
                result.append(problem_text)

            return "\n".join(result)
        except Exception as e:
            return f"문제 추천 실패: {str(e)}"

    def _generate_problem(self, student_id: str, area: str, difficulty: str = None, topic: str = None, num_speakers: int = 2) -> str:
        """AI 문제 생성 실행 (o4-mini - 빠른 추론 모델)"""
        try:
            # topic이 없으면 다양한 주제 중 랜덤 선택
            if not topic:
                import random
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
                    import re
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
        import re
        import json

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
                content = llm_response.choices[0].message.content
                # Extract JSON from response (handle markdown code blocks)
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    speakers_json = json.loads(json_match.group(0))
                else:
                    speakers_json = json.loads(content)

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

    def _evaluate_writing(self, prompt: str, student_answer: str, difficulty: str) -> str:
        """
        서술형 쓰기 답안 평가 (o4-mini 추론 모델)

        평가 기준:
        - Grammar (문법): 15점
        - Vocabulary (어휘): 15점
        - Organization (구조): 20점
        - Content (내용): 30점
        - Fluency (유창성): 20점
        총 100점
        """
        try:
            evaluation_prompt = f"""You are an expert English writing evaluator for CEFR {difficulty} level students.

**Writing Prompt:**
{prompt}

**Student's Answer:**
{student_answer}

**Evaluation Task:**
Evaluate this student's writing comprehensively using the following criteria:

1. **Grammar (15 points)**: Accuracy of grammar, sentence structure, verb tenses
2. **Vocabulary (15 points)**: Range and appropriateness of vocabulary for {difficulty} level
3. **Organization (20 points)**: Logical flow, paragraph structure, coherence
4. **Content (30 points)**: Relevance to prompt, depth of ideas, completeness
5. **Fluency (20 points)**: Natural expression, readability, overall language flow

**Output Format (IMPORTANT):**
Provide your evaluation in the following structured format:

**Overall Score:** [X/100]

**Grammar (X/15):**
- Strengths: [brief]
- Weaknesses: [brief]

**Vocabulary (X/15):**
- Strengths: [brief]
- Weaknesses: [brief]

**Organization (X/20):**
- Strengths: [brief]
- Weaknesses: [brief]

**Content (X/30):**
- Strengths: [brief]
- Weaknesses: [brief]

**Fluency (X/20):**
- Strengths: [brief]
- Weaknesses: [brief]

**Key Recommendations:**
1. [First improvement suggestion]
2. [Second improvement suggestion]
3. [Third improvement suggestion]

**Corrected Version (if needed):**
[Provide a corrected/improved version of the student's writing, maintaining their ideas but fixing errors]
"""

            # o4-mini로 추론 기반 평가
            response = self.client.chat.completions.create(
                model="o4-mini",
                messages=[{"role": "user", "content": evaluation_prompt}],
                max_completion_tokens=2500
            )

            return response.choices[0].message.content

        except Exception as e:
            # Fallback to GPT-4o
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an expert English writing evaluator."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    temperature=0.3,  # Lower temperature for consistent evaluation
                    max_tokens=2000
                )
                return response.choices[0].message.content
            except Exception as fallback_error:
                return f"평가 실패: {str(e)}, Fallback 실패: {str(fallback_error)}"

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
                    "primary": "gpt-4.1-mini",
                    "all_used": used_models
                }
            }
        else:
            # Quick reply 없으면 일반 응답
            return {
                "message": content,
                "model_info": {
                    "primary": "gpt-4.1-mini",
                    "all_used": used_models
                }
            }

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Function 실행"""

        # 함수 타입 분류
        db_functions = ["get_student_context", "recommend_problems"]
        generation_functions = ["generate_problem", "evaluate_writing"]
        external_api_functions = ["lookup_word", "fetch_news", "analyze_text_difficulty", "check_grammar"]

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

        if function_name == "get_student_context":
            # 벡터 검색을 위해 현재 사용자 메시지 전달
            result = self._get_student_context(query_text=self.current_user_message, **arguments)
        elif function_name == "recommend_problems":
            result = self._recommend_problems(**arguments)
        elif function_name == "generate_problem":
            result = self._generate_problem(**arguments)
        elif function_name == "evaluate_writing":
            result = self._evaluate_writing(**arguments)
        elif function_name == "lookup_word":
            result = self._lookup_word(**arguments)
        elif function_name == "fetch_news":
            result = self._fetch_news(**arguments)
        elif function_name == "analyze_text_difficulty":
            result = self._analyze_text_difficulty(**arguments)
        elif function_name == "check_grammar":
            result = self._check_grammar(**arguments)
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
        학생과 채팅 (Function Calling)

        Args:
            student_id: 학생 ID
            message: 학생의 메시지
            chat_history: 이전 대화 기록 (선택)
            session_id: 세션 ID (오디오 추적용, 선택)

        Returns:
            Dict with 'message' and 'model_info'
        """
        try:
            # ========== 요청 시작 로깅 ==========
            print_box(
                "🎓 STUDENT CHATBOT REQUEST",
                f"Student ID: {student_id}\n"
                f"Message: {message}\n"
                f"Session ID: {session_id or 'None'}",
                Colors.CYAN
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
                print("🔍 문제 유형 선택 요청 감지")
                return {
                    "message": "어떤 유형의 문제를 내드릴까요?",
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
                role="student_agent",
                model=primary_model,
                context={"student_id": student_id}
            )

            # 메시지 구성 (멀티턴 지원)
            messages = [{"role": "system", "content": system_prompt}]

            # 대화 히스토리 추가
            if chat_history:
                messages.extend(chat_history)

            # 최신 사용자 메시지 추가
            messages.append({"role": "user", "content": message})

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
                    tool_choice="auto",  # 자동으로 도구 선택
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
                    if function_name == "generate_problem":
                        used_models.append("o4-mini")
                    elif function_name == "evaluate_writing":
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

                return self._parse_quick_reply(response_content, list(set(used_models)))
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

                return self._parse_quick_reply(response_content, list(set(used_models)))

        except Exception as e:
            return {
                "message": f"죄송합니다. 오류가 발생했습니다: {str(e)}",
                "model_info": {"primary": "error", "all_used": []}
            }


# 싱글톤 인스턴스
_student_agent_service = None


def get_student_agent_service() -> StudentAgentService:
    """Student Agent 서비스 싱글톤 인스턴스 가져오기"""
    global _student_agent_service
    if _student_agent_service is None:
        _student_agent_service = StudentAgentService()
    return _student_agent_service
