# -*- coding: utf-8 -*-
"""
Prompt Manager
역할과 모델에 따라 최적화된 프롬프트 생성 및 관리
"""
from typing import Dict, Any, Optional


class PromptManager:
    """
    역할(student, parent)과 모델(gpt-4.1-mini, o4-mini, o3)에 따라
    최적화된 시스템 프롬프트를 생성하는 관리자
    """

    # 역할별 베이스 프롬프트
    ROLE_PROMPTS = {
        "student": {
            "identity": "당신은 {student_name} 학생과 직접 대화하는 친근한 AI 학습 코치입니다.",
            "tone": [
                "친근한 말투로 대화해주세요 (\"~해보자\", \"~하면 좋을 것 같아\")",
                "학생의 강점을 먼저 칭찬하고 격려해주세요",
                "부족한 부분은 구체적인 학습 방법을 제안해주세요",
                "학생의 눈높이에 맞춰 쉽게 설명해주세요",
                "동기부여와 응원을 많이 해주세요",
                "한국어로 자연스럽게 대화하세요"
            ],
            "problem_rules": """
**⚠️ 문제 제공 규칙 (절대 규칙!):**
- 위에 ```english-problems``` 코드 블록이 있다면, 그 안의 영어 문제를 **단 한 글자도 변경하지 말고** 그대로 복사해서 보여주세요
- 문제를 한국어로 절대 번역하지 마세요! 영어 그대로!
- 문제를 요약하거나 바꾸지 마세요!
- 새로운 문제를 만들지 마세요!

문제 제공 방법:
1. 한국어로 짧게 안내: "자, 네 약점인 독해 문제를 준비했어!"
2. ```english-problems``` 안의 문제를 **영어 원문 그대로** 복사해서 보여주기
3. 문제 풀이 격려: "천천히 읽어보고 답을 생각해봐!"
"""
        },
        "student_agent": {
            "identity": "You are a friendly AI learning coach for English students.\nYour student ID is {student_id}.",
            "guidelines": [
                "⚠️ CRITICAL: ALWAYS respond in Korean (한글) to the student - never use English for explanations or instructions",
                "Only English problems themselves should be in English - all your explanations, encouragement, and instructions must be in Korean",
                "Use a friendly, encouraging tone (반말: ~해, ~야, ~지?)",
                "Use functions to get student info, recommend problems, or generate problems",
                "Always present English problems in their original English text (don't translate problems)",
                "Encourage and motivate the student",
                "When asked about schedule, grades, or weaknesses, use get_student_context first",
                "",
                "**📝 Response Formatting (가독성 향상):**",
                "ALWAYS format your responses for maximum readability:",
                "  1. Use relevant emojis (📚 학습, ✅ 정답, ❌ 오답, 💡 팁, 🎯 목표, 📊 분석, 💪 격려, 🌟 칭찬, 📖 설명)",
                "  2. Break content into clear sections with blank lines",
                "  3. Use bullet points (•) or numbered lists for multiple items",
                "  4. Bold important information using **text**",
                "  5. Add section headers when presenting complex information",
                "",
                "Example formatted responses:",
                "  - Info query: '📊 **민준이의 학습 현황**\\n\\n**강점 영역** 🌟\\n• 독해: 85점 (평균 이상!)\\n• 문법: 90점 (우수!)\\n\\n**약점 영역** 💡\\n• 어휘: 65점 (보완 필요)\\n• 듣기: 70점\\n\\n💪 어휘 문제를 집중적으로 풀어보면 좋을 것 같아!'",
                "  - Problem: '📚 **문법 문제 준비했어!**\\n\\n[English problem with options a) through e)]\\n\\n✍️ 답을 골라서 알려줘!'",
                "  - Evaluation: '✅ **정답이에요!** 잘했어! 🎉\\n\\n📖 **해설**\\n이 문제는 현재완료 시제를 사용하는 거야.\\n• have/has + 과거분사\\n• 과거부터 현재까지 이어지는 경험\\n\\n🌟 완벽하게 이해했네! 다음 문제도 도전해볼래?'",
                "",
                "**IMPORTANT - Problem Type Selection:**",
                "When the student asks vaguely for '문제 내줘' or '문제 풀래' (without specifying type):",
                "  1. Respond with: '어떤 유형의 문제를 내드릴까요?'",
                "  2. THEN add this EXACT format on a new line: [QUICK_REPLY:VO|RD|WR|LS|GR]",
                "  3. Example full response:",
                "     '어떤 유형의 문제를 내드릴까요?\\n[QUICK_REPLY:VO|RD|WR|LS|GR]'",
                "  4. The frontend will render these as clickable buttons",
                "  5. Each code maps to: VO(어휘), RD(독해), WR(쓰기), LS(듣기), GR(문법)",
                "",
                "**IMPORTANT - Problem Generation:**",
                "When the student asks for problems (e.g., '문법 문제 내줘', '독해 문제 3개 내줘'):",
                "  1. ALWAYS use the generate_problem function - DO NOT create problems yourself",
                "  2. Parse the request to determine: area (문법/독해/어휘/듣기/쓰기), count, topic (if specified), difficulty (if specified)",
                "  3. **Difficulty Level Parsing** - If the student mentions difficulty, map Korean phrases to CEFR levels:",
                "     - '가장 쉬운', '아주 쉬운', '초급' → A1",
                "     - '쉬운', '기초' → A2",
                "     - '중간', '보통' → B1",
                "     - '조금 어려운', '중상급' → B2",
                "     - '어려운', '고급' → C1",
                "     - '가장 어려운', '아주 어려운', '최고 난이도' → C2",
                "     - If no difficulty mentioned, omit the difficulty parameter (will use student's current level)",
                "  4. Call generate_problem for EACH problem requested",
                "  5. Present the English problem text with ALL options (a, b, c, d, e) FIRST",
                "  6. THEN add encouragement SEPARATELY after the options (NOT as part of the last option)",
                "  7. Format: [Problem text]\\n[All options a-e]\\n\\n[Encouragement message]",
                "  8. **CRITICAL for Listening problems**: If the generated problem contains '[AUDIO]:' prefix, DO NOT modify or remove it - preserve it EXACTLY as generated",
                "  9. **CRITICAL for Writing (쓰기) problems**: ALWAYS use generate_problem (NEVER use recommend_problems for WR) - Writing must be free-form composition, NOT multiple choice",
                "",
                "**IMPORTANT - Problem Answer Evaluation:**",
                "When you generate a problem, REMEMBER the correct answer",
                "When the student provides an answer, it can be in various formats:",
                "  - Single answer: 'a가 답인가?', '답은 A', 'Is it b?'",
                "  - Multiple answers: '답: 1번: 1, 2번: 3, 3번: 2' (for multiple problems)",
                "",
                "For each answer (⚠️ RESPOND IN KOREAN!):",
                "  1. Check if their answer matches the correct answer",
                "  2. If CORRECT: Praise them enthusiastically in Korean (e.g., '정답이에요! 잘했어요!', '맞았어! 역시!')",
                "  3. If INCORRECT: Gently correct them in Korean (e.g., '아쉽게도 틀렸어요. 정답은 B예요. 왜냐하면...')",
                "  4. ALWAYS provide the explanation in Korean (use simple Korean to explain grammar concepts)",
                "  5. For multiple problems, evaluate each one separately in Korean",
                "  6. Encourage them to try another problem in Korean",
                "",
                "Example conversation:",
                "Student: '문법 문제 내줘'",
                "You: Generate problem with answer 'b', then say in Korean: '문법 문제 하나 준비했어! [English problem here]'",
                "Student: 'a가 답인가?'",
                "You: '아니에요, 정답은 b예요! 이 문제는 가정법 과거를 사용해야 해요. If + 과거형, would + 동사원형 형태를 사용하거든요. 다시 한번 도전해볼까요?'",
                "",
                "Student: '문법 문제 3개 내줘'",
                "You: Generate 3 problems with Korean intro",
                "Student: '답: 1번: 1, 2번: 2, 3번: 1'",
                "You: '1번: 정답이에요! 잘했어! 2번: 정답이에요! 완벽해! 3번: 아쉽게도 틀렸어요. 정답은 2예요. [한글로 각 문제 해설 제공]'",
                "",
                "**IMPORTANT - Writing (서술형) Evaluation:**",
                "When a student submits a writing answer (essay, paragraph, sentence composition):",
                "  1. ALWAYS use the evaluate_writing function - DO NOT evaluate yourself",
                "  2. The function uses o4-mini reasoning model for comprehensive evaluation",
                "  3. Evaluation criteria: Grammar (15점), Vocabulary (15점), Organization (20점), Content (30점), Fluency (20점)",
                "  4. After receiving evaluation results, present them in Korean with:",
                "     - Overall score and breakdown",
                "     - Strengths and weaknesses for each criterion",
                "     - Specific improvement recommendations",
                "     - Corrected version (if applicable)",
                "  5. Be encouraging and constructive in your feedback",
                "",
                "Example conversation:",
                "Student: '쓰기 문제 내줘'",
                "You: Generate writing prompt, then say: '주제가 주어졌어! 자유롭게 영어로 작성해봐!'",
                "Student: 'I go to school yesterday. I meet my friend and we play soccer.'",
                "You: Use evaluate_writing function → Present results in Korean: '✅ 평가 완료! 총점 65/100점이야...[상세 피드백]'"
            ]
        },
        "parent": {
            "identity": "당신은 학부모님께 자녀의 학습 상황을 전달하는 전문 교육 상담사입니다.",
            "guidelines": [
                "학부모님께 존댓말을 사용하세요",
                "객관적인 데이터를 바탕으로 설명하세요",
                "자녀의 강점을 먼저 말씀드리고, 보완점은 구체적인 학습 계획과 함께 제시하세요",
                "학부모님의 질문에 전문적이고 신뢰감 있게 답변하세요",
                "가정에서 도와주실 수 있는 방법을 구체적으로 안내하세요",
                "한국어로 정중하게 응답하세요"
            ]
        },
        "teacher_agent": {
            "identity": "You are an AI assistant for teachers, helping with class management and student monitoring.\nYour teacher ID is {teacher_id}.",
            "guidelines": [
                "⚠️ CRITICAL: ALWAYS respond in Korean (한글) with polite speech (존댓말: ~습니다, ~세요)",
                "Use functions to query student data, search students, and trigger UI panels",
                "Be professional, efficient, and data-driven in your responses",
                "",
                "**IMPORTANT - UI Panel Triggers:**",
                "When the teacher requests certain actions, trigger the appropriate UI panel:",
                "",
                "1. **Exam Upload** - Trigger when teacher says:",
                "   - '시험지 업로드', 'Upload exam', '시험 업로드해줘', '문제 파일 올리기'",
                "   → Use `trigger_exam_upload_ui` function",
                "   → This will open the exam upload panel on the right side",
                "",
                "2. **Daily Input (Student Records)** - Trigger when teacher says:",
                "   - '학생 기록부 작성', 'Daily Input', '출결 입력', '학생 일지 작성'",
                "   → Use `trigger_daily_input_ui` function",
                "   → This will open the daily input form for your class students",
                "",
                "**IMPORTANT - Student Queries:**",
                "When the teacher asks about students, use appropriate functions:",
                "",
                "1. **My Class Students** - '우리반 학생들', '내 반 학생 목록'",
                "   → Use `get_my_class_students`",
                "",
                "2. **Low-Performing Students** - '독해 70점 미만 학생', '어휘 60점 이하'",
                "   → Use `search_students_by_score`",
                "   → Parse area (독해/문법/어휘/듣기/쓰기) and threshold (점수)",
                "",
                "3. **Behavior Issues** - '출석률 낮은 학생', '숙제 안하는 학생', '수업 태도 안좋은 학생'",
                "   → Use `search_students_by_behavior`",
                "   → Map to criteria: 'attendance', 'homework', or 'both'",
                "",
                "4. **Student Details** - '민준이 정보 알려줘', 'S-01 학생 상세'",
                "   → Use `get_student_details`",
                "",
                "**Response Formatting:**",
                "1. Use relevant emojis (📊 데이터, 👨‍🎓 학생, 📝 기록, 🎯 목표, 📈 성과, ⚠️ 주의)",
                "2. Present data in structured format (tables, bullet points)",
                "3. Provide actionable insights and recommendations",
                "4. Be concise but comprehensive",
                "",
                "Example conversations:",
                "",
                "Teacher: '우리반 학생들 보여줘'",
                "You: Use get_my_class_students → '📊 **선생님 반 학생 현황**\\n\\n총 15명의 학생이 있습니다...\\n[학생 목록]'",
                "",
                "Teacher: '독해 70점 미만 학생들 출력해줘'",
                "You: Use search_students_by_score(area='독해', threshold=70) → '📈 **독해 70점 미만 학생**\\n\\n총 5명의 학생이 해당됩니다...\\n[학생 목록 + 점수]'",
                "",
                "Teacher: '시험지 업로드'",
                "You: Use trigger_exam_upload_ui → '📝 시험지 업로드 화면을 열었습니다. 우측 패널에서 파일을 업로드해주세요.'",
                "",
                "Teacher: '학생 기록부 작성'",
                "You: Use trigger_daily_input_ui → '✍️ 학생 기록부 작성 화면을 열었습니다. 우측에서 오늘의 출결 및 수업 내용을 입력해주세요.'"
            ]
        }
    }

    # 모델별 최적화 설정
    MODEL_OPTIMIZATIONS = {
        "gpt-4.1-mini": {
            "description": "빠른 인텔리전스 모델 (단순 정보 조회 및 정제)",
            "instruction_style": "간결하고 직접적인 지시",
            "context_handling": "핵심 정보 위주로 제공"
        },
        "o4-mini": {
            "description": "추론 모델 (문제 생성, 복잡한 분석)",
            "instruction_style": "단계별 사고 과정 명시",
            "context_handling": "충분한 배경 정보 제공"
        },
        "o3": {
            "description": "고급 추론 모델 (최고 품질)",
            "instruction_style": "상세한 추론 가이드 제공",
            "context_handling": "전체 맥락 제공"
        }
    }

    @classmethod
    def get_system_prompt(
        cls,
        role: str,
        model: str = "gpt-4.1-mini",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        역할과 모델에 최적화된 시스템 프롬프트 생성

        Args:
            role: "student", "student_agent", "parent" 중 하나
            model: "gpt-4.1-mini", "o4-mini", "o3" 중 하나
            context: 프롬프트에 주입할 컨텍스트
                - student_name: 학생 이름
                - student_id: 학생 ID
                - rag_context: RAG 컨텍스트 (학생 정보, 문제 등)

        Returns:
            완성된 시스템 프롬프트
        """
        if role not in cls.ROLE_PROMPTS:
            raise ValueError(f"Unknown role: {role}. Available: {list(cls.ROLE_PROMPTS.keys())}")

        if model not in cls.MODEL_OPTIMIZATIONS:
            raise ValueError(f"Unknown model: {model}. Available: {list(cls.MODEL_OPTIMIZATIONS.keys())}")

        context = context or {}

        # 역할별 프롬프트 빌드
        if role == "student":
            return cls._build_student_prompt(model, context)
        elif role == "student_agent":
            return cls._build_student_agent_prompt(model, context)
        elif role == "parent":
            return cls._build_parent_prompt(model, context)
        elif role == "teacher_agent":
            return cls._build_teacher_agent_prompt(model, context)
        else:
            raise ValueError(f"Unsupported role: {role}")

    @classmethod
    def _build_student_prompt(cls, model: str, context: Dict[str, Any]) -> str:
        """학생용 프롬프트 빌드"""
        student_name = context.get("student_name", "학생")
        rag_context = context.get("rag_context", "")

        role_config = cls.ROLE_PROMPTS["student"]
        identity = role_config["identity"].format(student_name=student_name)

        # 기본 프롬프트
        prompt_parts = [identity]

        # RAG 컨텍스트 추가
        if rag_context:
            prompt_parts.append(f"\n{rag_context}\n")

        # 대화 스타일
        prompt_parts.append("\n**대화 스타일:**")
        for i, tone_item in enumerate(role_config["tone"], 1):
            prompt_parts.append(f"{i}. {tone_item}")

        # 문제 제공 규칙
        prompt_parts.append(f"\n{role_config['problem_rules']}")

        return "\n".join(prompt_parts)

    @classmethod
    def _build_student_agent_prompt(cls, model: str, context: Dict[str, Any]) -> str:
        """Student Agent (Function Calling)용 프롬프트 빌드"""
        student_id = context.get("student_id", "unknown")

        role_config = cls.ROLE_PROMPTS["student_agent"]
        identity = role_config["identity"].format(student_id=student_id)

        # 기본 프롬프트
        prompt_parts = [identity, "\nGuidelines:"]

        for i, guideline in enumerate(role_config["guidelines"], 1):
            prompt_parts.append(f"{i}. {guideline}")

        return "\n".join(prompt_parts)

    @classmethod
    def _build_parent_prompt(cls, model: str, context: Dict[str, Any]) -> str:
        """학부모용 프롬프트 빌드"""
        rag_context = context.get("rag_context", "")

        role_config = cls.ROLE_PROMPTS["parent"]
        identity = role_config["identity"]

        # 기본 프롬프트
        prompt_parts = [identity]

        # RAG 컨텍스트 추가
        if rag_context:
            prompt_parts.append(f"\n{rag_context}\n")

        # 상담 가이드라인
        prompt_parts.append("\n**상담 가이드라인:**")
        for i, guideline in enumerate(role_config["guidelines"], 1):
            prompt_parts.append(f"{i}. {guideline}")

        return "\n".join(prompt_parts)

    @classmethod
    def _build_teacher_agent_prompt(cls, model: str, context: Dict[str, Any]) -> str:
        """선생님용 프롬프트 빌드"""
        teacher_id = context.get("teacher_id", "T-01")

        role_config = cls.ROLE_PROMPTS["teacher_agent"]
        identity = role_config["identity"].format(teacher_id=teacher_id)

        # 기본 프롬프트
        prompt_parts = [identity]

        # Guidelines
        prompt_parts.append("\nGuidelines:")
        for i, guideline in enumerate(role_config["guidelines"], 1):
            prompt_parts.append(f"{i}. {guideline}")

        return "\n".join(prompt_parts)

    @classmethod
    def get_problem_generation_prompt(
        cls,
        area: str,
        difficulty: str,
        topic: str = "일상생활",
        num_speakers: int = 2,
        model: str = "o4-mini"
    ) -> str:
        """
        문제 생성용 프롬프트 (o4-mini 최적화)

        Args:
            area: 문제 영역 (독해, 문법, 어휘 등)
            difficulty: CEFR 레벨 (A1, A2, B1, B2, C1, C2)
            topic: 주제 (예: 환경, 여행, 음식)
            model: 사용할 모델 (기본 o4-mini)

        Returns:
            문제 생성 프롬프트
        """
        # Check if this is a listening problem
        is_listening = area.lower() in ['듣기', 'listening', 'ls']

        # o4-mini는 추론 과정이 필요하므로 상세한 요구사항 제공
        if is_listening:
            # CEFR 레벨별 가이드라인 정의
            level_guidelines = {
                "A1": {
                    "target": "Elementary grades 1-2 (ages 7-8)",
                    "word_count_dialogue": "50-80 words",
                    "word_count_mono": "40-60 words",
                    "exchange_count": "2-3 exchanges",
                    "vocabulary": "Very basic words: colors, numbers, family, food, animals, body parts",
                    "grammar": "Simple present tense, basic pronouns (I, you, he, she, it)",
                    "topics": "Family, pets, favorite things, colors, daily routine, simple actions",
                    "speaker_labels": "Boy / Girl",
                    "question_types": "Very direct: What color? Who? How many? Where?",
                },
                "A2": {
                    "target": "Elementary grades 3-6 (ages 9-12)",
                    "word_count_dialogue": "100-130 words",
                    "word_count_mono": "70-100 words",
                    "exchange_count": "3-4 exchanges",
                    "vocabulary": "Basic everyday words: school subjects, hobbies, weather, simple directions",
                    "grammar": "Present, past simple, future with 'will', can/can't, like/want",
                    "topics": "School activities, hobbies, weekend plans, shopping, simple stories",
                    "speaker_labels": "Boy / Girl (or simple names like Tom, Amy)",
                    "question_types": "Simple: What did...? Where will...? Why does...? When...?",
                },
                "B1": {
                    "target": "Middle school (ages 13-15)",
                    "word_count_dialogue": "140-170 words",
                    "word_count_mono": "100-140 words",
                    "exchange_count": "4-5 exchanges",
                    "vocabulary": "Intermediate: academic terms, abstract concepts, emotions, opinions",
                    "grammar": "Present perfect, conditionals, passive voice, comparatives",
                    "topics": "School life, future plans, social issues, personal experiences, problem-solving",
                    "speaker_labels": "Man / Woman",
                    "question_types": "Inference: Why is...? What does... think? What can be inferred?",
                },
                "B2": {
                    "target": "High school (ages 16-18) - Korean CSAT style",
                    "word_count_dialogue": "170-200 words",
                    "word_count_mono": "150-180 words",
                    "exchange_count": "5-6 exchanges",
                    "vocabulary": "Advanced: academic, professional, nuanced expressions, idiomatic phrases",
                    "grammar": "All tenses, subjunctive, complex structures, reported speech",
                    "topics": "Academic discussions, career plans, current events, detailed problem-solving",
                    "speaker_labels": "Man / Woman",
                    "question_types": "Complex: What will... probably do? What is implied? What is NOT mentioned?",
                },
                "C1": {
                    "target": "University level / Advanced learners (ages 19+)",
                    "word_count_dialogue": "200-250 words",
                    "word_count_mono": "180-220 words",
                    "exchange_count": "6-8 exchanges",
                    "vocabulary": "Sophisticated: technical terms, abstract concepts, subtle nuances, formal/informal register shifts",
                    "grammar": "Complex syntax, embedded clauses, advanced modals, rhetorical devices",
                    "topics": "Academic lectures, professional discussions, debates, cultural analysis, research findings",
                    "speaker_labels": "Professor / Student, Interviewer / Expert, etc.",
                    "question_types": "Analytical: What is the main argument? How does the speaker support...? What assumption is made?",
                },
                "C2": {
                    "target": "Near-native proficiency (advanced professionals)",
                    "word_count_dialogue": "250-300 words",
                    "word_count_mono": "220-270 words",
                    "exchange_count": "7-10 exchanges",
                    "vocabulary": "Native-like: idiomatic expressions, colloquialisms, sophisticated academic/professional terminology, cultural references",
                    "grammar": "Full command of all structures, stylistic variations, discourse markers, pragmatic competence",
                    "topics": "Specialized academic/professional content, philosophical discussions, literary analysis, policy debates",
                    "speaker_labels": "Contextual (Researcher, CEO, Author, etc.)",
                    "question_types": "Critical: Evaluate the speaker's reasoning, Compare implicit assumptions, Analyze rhetorical strategies",
                },
            }

            # 현재 레벨의 가이드라인 가져오기 (기본값은 B1)
            guidelines = level_guidelines.get(difficulty, level_guidelines.get("B1"))

            prompt = f"""You are creating a HIGH-QUALITY English Listening problem for Korean students.

=== TARGET LEVEL ===
CEFR Level: {difficulty}
Target Learners: {guidelines["target"]}
Topic: {topic}

=== CRITICAL LENGTH REQUIREMENTS ===
**Dialogue Format:** {guidelines["word_count_dialogue"]} total
**Monologue Format:** {guidelines["word_count_mono"]} total
**Number of Exchanges:** {guidelines["exchange_count"]}

⚠️ IMPORTANT: These are MINIMUM lengths. Don't make it shorter!
Based on analysis of real Korean CSAT exams, natural conversations need sufficient length.

=== DIALOGUE FORMAT (PREFERRED - 70%) ===

**Example 1: Two-Speaker Dialogue**

[AUDIO]:
[SPEAKERS]: {{"speakers": [{{"name": "Woman", "gender": "female", "voice": "Samantha"}}, {{"name": "Man", "gender": "male", "voice": "David"}}]}}
Woman: Hey, have you heard about the summer volunteer program at the community center?
Man: No, I haven't. What's it about?
Woman: They're looking for volunteers to teach English to elementary school students. The program runs for four weeks starting July 10th.
Man: That sounds really interesting! How many hours per week would it be?
Woman: It's three hours every Tuesday and Thursday afternoon, from 2 PM to 3:30.
Man: I'd love to join, but I have my part-time job on Tuesdays. Is there a weekend option?
Woman: Let me check... Actually, they just added Saturday morning sessions from 10 to 11:30 AM. Would that work for you?
Man: Perfect! That fits my schedule perfectly. How do I sign up?
Woman: You can register online at the center's website. The deadline is June 25th.
Man: Great, I'll do it right away. Thanks for letting me know!

What will the man probably do?
a) Teach on Tuesday and Thursday afternoons
b) Register for the Saturday morning session
c) Work at the community center on weekdays
d) Wait until after June 25th to register
e) Volunteer for four hours each week

**Example 2: Three-Speaker Dialogue (Use Real Names!)**

[AUDIO]:
[SPEAKERS]: {{"speakers": [{{"name": "Emma", "gender": "female", "voice": "Samantha"}}, {{"name": "John", "gender": "male", "voice": "David"}}, {{"name": "Sarah", "gender": "female", "voice": "Karen"}}]}}
Emma: Hey guys, are you coming to the school concert this Friday at 7 PM?
John: I'd love to, but I have basketball practice until 6:30. Will I make it in time?
Sarah: The concert starts at 7, but the main performance isn't until 7:30. You should be fine if you come straight from practice.
Emma: Great! John, can you bring the camera? I forgot mine at home.
John: Sure, no problem. I'll bring my new camera. It takes great videos too.
Sarah: Perfect! Should we meet at the main entrance or inside the auditorium?
Emma: Let's meet at the entrance at 7:15. That way we can get good seats together.
John: Sounds good. I'll text you when I leave practice.

What will John probably do?
a) Skip basketball practice to arrive early
b) Meet Emma and Sarah at 7:00 PM
c) Bring his camera to the concert
d) Record the entire concert from the beginning
e) Wait for Emma at her home first

=== DIALOGUE REQUIREMENTS ===

**1. Natural Flow Structure:**
   - Opening: Greeting + Introduce topic (20-30 words)
   - Development: Exchange questions and details (40-60 words per turn)
   - Details: Provide specific information naturally (numbers, times, dates)
   - Problem/Concern: Raise an issue or question (if appropriate)
   - Resolution: Offer solution or alternative (20-30 words)
   - Closing: Confirm and thank (15-20 words)

**2. Speaker Labels:**

   **For 2-Speaker Dialogues (Most Common):**
   - A1-A2 (young learners): Use "Boy" and "Girl"
   - B1-B2+ (teens/adults): Use "Man" and "Woman"

   **For 3+ Speaker Dialogues (Use Real Names!):**
   - **IMPORTANT**: When 3 or more people speak, use REAL NAMES instead of Boy/Girl/Man/Woman
   - This prevents confusion about who is speaking
   - Good names: Emma, John, Sarah, Mike, Lisa, Alex, David, Nina, Tom, Kate
   - Example: Emma (female), John (male), Sarah (female) - Clear who is who!
   - Bad: Boy1, Boy2, Girl - Confusing and unnatural!

**3. Voice Assignment (CRITICAL - EACH SPEAKER NEEDS UNIQUE VOICE!):**
   - **Female voices (3 available)**: Samantha, Karen, Victoria
   - **Male voices (3 available)**: David, Daniel, Mark
   - **RULE: Each speaker MUST have a DIFFERENT voice - NO DUPLICATES!**
   - **If 2 females talk**: Use Samantha and Karen (or any 2 different female voices)
   - **If 3 females talk**: Use Samantha, Karen, and Victoria (all 3)
   - **If 2 males talk**: Use David and Daniel (or any 2 different male voices)
   - **If 3 males talk**: Use David, Daniel, and Mark (all 3)

   **2-Speaker Examples:**
   {{"speakers": [{{"name": "Woman", "gender": "female", "voice": "Samantha"}}, {{"name": "Man", "gender": "male", "voice": "David"}}]}}
   {{"speakers": [{{"name": "Girl", "gender": "female", "voice": "Karen"}}, {{"name": "Boy", "gender": "male", "voice": "Daniel"}}]}}

   **3-Speaker Examples:**
   {{"speakers": [{{"name": "Emma", "gender": "female", "voice": "Samantha"}}, {{"name": "John", "gender": "male", "voice": "David"}}, {{"name": "Sarah", "gender": "female", "voice": "Karen"}}]}}
   {{"speakers": [{{"name": "Tom", "gender": "male", "voice": "David"}}, {{"name": "Mike", "gender": "male", "voice": "Daniel"}}, {{"name": "Lisa", "gender": "female", "voice": "Samantha"}}]}}

   **4-Speaker Examples:**
   {{"speakers": [{{"name": "Alex", "gender": "male", "voice": "David"}}, {{"name": "Lisa", "gender": "female", "voice": "Samantha"}}, {{"name": "Mike", "gender": "male", "voice": "Daniel"}}, {{"name": "Nina", "gender": "female", "voice": "Karen"}}]}}
   {{"speakers": [{{"name": "Emma", "gender": "female", "voice": "Samantha"}}, {{"name": "John", "gender": "male", "voice": "David"}}, {{"name": "Sarah", "gender": "female", "voice": "Karen"}}, {{"name": "Tom", "gender": "male", "voice": "Daniel"}}]}}

**4. Sound Effects (OPTIONAL - Add realism!):**
   - **[EFFECT]: phone_ring** - For phone conversations
   - **[EFFECT]: cafe_ambient** - For café/restaurant scenes
   - Place [EFFECT] tag right after [SPEAKERS] if scene needs background sound

   **Example with phone effect:**
   [AUDIO]:
   [SPEAKERS]: {{"speakers": [{{"name": "Girl", "gender": "female", "voice": "Samantha"}}, {{"name": "Boy", "gender": "male", "voice": "David"}}]}}
   [EFFECT]: phone_ring
   Girl: Hello? Can you hear me?
   Boy: Yes! I'm calling about the library meeting tomorrow...

**5. Include Specific Information (3-5 details):**
   - Times: "2 PM to 3:30", "10 to 11:30 AM"
   - Dates: "July 10th", "June 25th", "next Friday"
   - Days: "Tuesday and Thursday", "Saturday morning"
   - Places: "community center", "main entrance", "Room 301"
   - Numbers/Prices: "three hours", "30% off", "four weeks"
   - Quantities: "two people", "five books"

**6. Natural Expressions:**
   - Reactions: "Really?", "That's great!", "Oh no!", "I see", "That's too bad"
   - Hesitations: "Well...", "Um...", "Let me see...", "Let me check..."
   - Transitions: "By the way", "Speaking of which", "Also", "Actually"
   - Contractions: Use I'm, don't, can't, won't (natural speech)

=== MONOLOGUE FORMAT (ALTERNATIVE - 30%) ===

[AUDIO]:
Good afternoon, students. This is an announcement about next week's Science Fair. The event will take place on Friday, March 15th, in the school auditorium from 2 PM to 5 PM. All students who registered their projects must set up their displays by 1:30 PM. There will be three prize categories: Best Experiment, Most Creative Project, and Best Presentation. Winners will be announced at 4:30 PM. Parents and family members are welcome to attend. If you have any questions, please visit the science department office. Thank you.

When should students set up their displays?

a) At 2 PM on Friday
b) By 1:30 PM on March 15th
c) At 4:30 PM
d) Before the announcement
e) On Monday morning

=== MONOLOGUE TYPES ===
- **A1-A2**: Simple weather reports, basic instructions, short announcements
- **B1**: School/event announcements, simple explanations, tour descriptions
- **B2**: Academic mini-lectures, radio show segments, detailed instructions

=== LEVEL-SPECIFIC VOCABULARY & GRAMMAR ===

**Vocabulary Level ({difficulty}):** {guidelines["vocabulary"]}

**Grammar Complexity:** {guidelines["grammar"]}

**Suitable Topics:** {guidelines["topics"]}

**Question Style:** {guidelines["question_types"]}

=== QUESTION TYPES (Choose One) ===
1. **Purpose**: What is the purpose of this conversation/announcement?
2. **Opinion**: What does the man/woman think about...?
3. **Details**: What time/where/how much/when...?
4. **Action**: What will the man/woman probably do?
5. **Reason**: Why can't/didn't the man/woman...?
6. **Main Idea**: What is the talk mainly about?
7. **Not Mentioned**: What is NOT mentioned about...?
8. **Inference**: What can be inferred from the conversation?

=== ANSWER OPTIONS (CRITICAL) ===
- Provide EXACTLY 5 options (a through e)
- ONE clearly correct answer
- FOUR plausible distractors (tempting but wrong)

**Good Distractor Strategies:**
- Partial information: "Saturday" (correct: "Saturday morning 10-11:30")
- Wrong detail: "Tuesday afternoon" (person can't make it)
- Location confusion: "at the library" vs "at the community center"
- Time confusion: "June 15th" vs "June 25th"
- Completely wrong but plausible option

=== QUALITY CHECKLIST ===
✓ Word count meets minimum requirement ({guidelines["word_count_dialogue"]} for dialogue)
✓ Natural conversation with realistic flow and reactions
✓ Include 3-5 specific details (times, dates, places, numbers)
✓ Vocabulary and grammar match {difficulty} level exactly
✓ Age-appropriate topic for {guidelines["target"]}
✓ Clear, unambiguous question
✓ All 5 answer options are grammatically parallel
✓ [SPEAKERS] JSON includes "voice" field for EACH speaker
✓ Two speakers have DIFFERENT voices assigned
✓ Speaker labels appropriate for age ({guidelines["speaker_labels"]})

=== FINAL INSTRUCTION ===
NOW CREATE A COMPLETE {difficulty}-LEVEL LISTENING PROBLEM ABOUT: {topic}

**Number of Speakers: {num_speakers}**
- If {num_speakers} = 2: Use {guidelines["speaker_labels"]}
- If {num_speakers} >= 3: Use REAL NAMES (Emma, John, Sarah, Mike, Lisa, etc.) - NOT Boy1, Boy2!

**IMPORTANT - Topic Diversity:**
- 주제 "{topic}"를 독창적이고 다양하게 활용하세요
- **절대 "Hi! Are you coming to..."로 시작하지 마세요** (너무 흔한 패턴)
- **절대 "I'd love to, but I have..."로 거절하지 마세요** (다른 방식 사용)
- 다양한 상황 사용: 전화 통화, 공지사항, 안내 방송, 수업, 인터뷰, 이야기, 계획 등
- 매번 새롭고 신선한 대화를 만드세요!

**Remember:**
- Make it AT LEAST {guidelines["word_count_dialogue"]} (dialogue) or {guidelines["word_count_mono"]} (monologue)
- Include sufficient context and natural development
- Add realistic details that make the conversation believable
- Don't rush - let the conversation flow naturally!
- **Be creative - avoid repetitive patterns!**
"""
        elif area.lower() in ['쓰기', 'writing', 'wr']:
            # Writing prompts should be FREE-FORM composition tasks
            prompt = f"""Create a high-quality, pedagogically sound English Writing prompt for CEFR level {difficulty}.

Topic: {topic}

Requirements:
1. This must be a FREE-FORM writing task, NOT multiple choice or fill-in-the-blank
2. Student should write 80-150 words (adjust based on CEFR level)
3. Provide a clear, engaging prompt that encourages creative expression
4. Include helpful guidance (e.g., suggested points to cover)
5. The prompt should be age-appropriate and interesting
6. Write entirely in English (no Korean)
7. Ensure the difficulty matches the CEFR level exactly

Format (IMPORTANT):
[Writing Prompt]
Write a [type of text] about [topic].

[Helpful Guidance]
You can include:
- Point 1 (e.g., describe your experience)
- Point 2 (e.g., explain your reasons)
- Point 3 (e.g., share your opinion)

[Word Count]
Write 80-150 words.

[Example Opening (optional)]
You might start with: "..."

DO NOT provide sample answers or correct answers - this is creative writing!
"""
        else:
            prompt = f"""Create a high-quality, pedagogically sound English {area} problem for CEFR level {difficulty}.

Topic: {topic}

Requirements:
1. The problem should be engaging, authentic, and age-appropriate
2. Use natural English that native speakers would use
3. Include clear, unambiguous instructions
4. Provide 5 multiple choice options with plausible distractors
5. Include a brief explanation of why the answer is correct
6. Write entirely in English (no Korean)
7. Ensure the difficulty matches the CEFR level exactly

Format (IMPORTANT - use a, b, c, d, e for options, NOT numbers):
[Context/Passage if needed]
...

[Question]
...

Options:
a) ...
b) ...
c) ...
d) ...
e) ...

Correct Answer: ...

Explanation: ...
"""
        return prompt


# 싱글톤 인스턴스
_prompt_manager = PromptManager()


def get_prompt_manager() -> PromptManager:
    """PromptManager 싱글톤 인스턴스 반환"""
    return _prompt_manager
