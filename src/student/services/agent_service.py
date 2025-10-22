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
from shared.services import get_graph_rag_service
from shared.prompts import PromptManager
from shared.services.tts_service import get_tts_service


class StudentAgentService:
    """학생 맞춤 Function Calling 에이전트"""

    def __init__(self):
        """초기화"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key)
        self.graph_rag_service = get_graph_rag_service()

        # Current user message for vector search context
        self.current_user_message = ""

        # Function definitions
        self.functions = self._create_functions()

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

        1. [AUDIO]: 패턴 확인 및 추가
        2. [SPEAKERS]: JSON 파싱 및 자동 생성
        3. 대화 형식 검증
        4. 첫 발화에 화자 이름 추가
        """
        import re
        import json

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
                audio_url = tts_service.get_or_create_audio(result)

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
        print(f"🔧 FUNCTION CALLED: {function_name}")
        print(f"📋 ARGUMENTS: {json.dumps(arguments, ensure_ascii=False)}")

        if function_name == "get_student_context":
            # 벡터 검색을 위해 현재 사용자 메시지 전달
            return self._get_student_context(query_text=self.current_user_message, **arguments)
        elif function_name == "recommend_problems":
            return self._recommend_problems(**arguments)
        elif function_name == "generate_problem":
            return self._generate_problem(**arguments)
        elif function_name == "evaluate_writing":
            return self._evaluate_writing(**arguments)
        else:
            return f"Unknown function: {function_name}"

    def chat(
        self,
        student_id: str,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        학생과 채팅 (Function Calling)

        Args:
            student_id: 학생 ID
            message: 학생의 메시지
            chat_history: 이전 대화 기록 (선택)

        Returns:
            Dict with 'message' and 'model_info'
        """
        try:
            # 현재 사용자 메시지 저장 (벡터 검색용)
            self.current_user_message = message

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
            # PromptManager를 사용해 시스템 프롬프트 생성
            system_prompt = PromptManager.get_system_prompt(
                role="student_agent",
                model="gpt-4.1-mini",
                context={"student_id": student_id}
            )

            # 메시지 구성 (멀티턴 지원)
            messages = [{"role": "system", "content": system_prompt}]

            # 대화 히스토리 추가
            if chat_history:
                messages.extend(chat_history)

            # 최신 사용자 메시지 추가
            messages.append({"role": "user", "content": message})

            # gpt-4.1-mini로 function calling (빠른 인텔리전스 모델)
            used_models.append("gpt-4.1-mini")
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

                # Function 결과를 바탕으로 최종 응답 생성 (DB 조회 정제)
                final_response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    temperature=0.7
                )

                response_content = final_response.choices[0].message.content
                return self._parse_quick_reply(response_content, list(set(used_models)))
            else:
                # Function 호출 없이 직접 응답
                return self._parse_quick_reply(assistant_message.content, ["gpt-4.1-mini"])

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
