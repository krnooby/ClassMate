# -*- coding: utf-8 -*-
"""
Teacher Router
선생님 전용 API 엔드포인트 (파일 업로드 및 파싱, Daily Input)
"""
from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
import shutil
import json
import subprocess
from pathlib import Path
from datetime import datetime, date
import openai
import os
from api.services.neo4j_service import Neo4jService

router = APIRouter()

def generate_student_summary(student_data: dict) -> str:
    """
    학생 데이터를 GPT-4.1-mini로 자연어 요약 생성

    Args:
        student_data: 학생 원본 데이터 (students_rag.json의 "원본데이터")

    Returns:
        자연어 요약 문자열
    """
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # 학생 데이터를 간결한 텍스트로 변환
        att = student_data.get("attendance", {})
        hw = student_data.get("homework", {})
        notes = student_data.get("notes", {})
        assess = student_data.get("assessment", {})
        radar = assess.get("radar_scores", {})
        overall = assess.get("overall", {})

        # 출석률 계산
        total_sessions = att.get("total_sessions", 0)
        absent = att.get("absent", 0)
        attendance_rate = round((total_sessions - absent) / total_sessions * 100, 1) if total_sessions > 0 else 0

        # 숙제 수행률 계산
        assigned = hw.get("assigned", 0)
        missed = hw.get("missed", 0)
        homework_rate = round((assigned - missed) / assigned * 100, 1) if assigned > 0 else 0

        # 강점/보완 영역 찾기
        scores = [(k, v) for k, v in radar.items()]
        scores_sorted = sorted(scores, key=lambda x: x[1], reverse=True)
        strengths = [scores_sorted[i][0] for i in range(min(2, len(scores_sorted)))]
        weaknesses = [scores_sorted[i][0] for i in range(max(0, len(scores_sorted)-1), len(scores_sorted))]

        prompt = f"""다음 학생 정보를 한 문장으로 간결하게 요약하세요.

학생: {student_data.get('name')}({student_data.get('student_id')}), {student_data.get('class_id')}, {student_data.get('grade_label')}({student_data.get('grade_code')}).
업데이트: {student_data.get('updated_at')}.
출결: {total_sessions}회 중 결석 {absent}회. 출석률 {attendance_rate}%.
숙제: {assigned}건 중 미제출 {missed}건. 수행률 {homework_rate}%.
전체 수준: CEFR {overall.get('cefr')}, 백분위 {overall.get('percentile_rank')}.
영역 점수: grammar {radar.get('grammar')}, vocabulary {radar.get('vocabulary')}, reading {radar.get('reading')}, listening {radar.get('listening')}, writing {radar.get('writing')}.
강점: {', '.join(strengths)}. 보완: {', '.join(weaknesses)}.
비고: 태도 {notes.get('attitude')}, 학교평가 {notes.get('school_exam_level')}, 진단평가 {notes.get('csat_level')}.

위 정보를 한 문장으로 요약:"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )

        summary = response.choices[0].message.content.strip()
        return summary

    except Exception as e:
        print(f"[ERROR] Failed to generate summary: {str(e)}")
        # 요약 생성 실패 시 기본 요약 반환
        return f"{student_data.get('name')}({student_data.get('student_id')}), {student_data.get('class_id')}, {student_data.get('grade_label')}. 업데이트 {student_data.get('updated_at')}."


class ParseJobResponse(BaseModel):
    """파싱 작업 응답"""
    job_id: str
    exam_id: str
    status: str  # "queued", "processing", "completed", "failed"
    message: str
    files: dict


class ParseStatusResponse(BaseModel):
    """파싱 상태 응답"""
    job_id: str
    status: str
    message: str
    progress: int  # 0-100
    results: Optional[dict] = None
    error: Optional[str] = None


# 작업 상태 저장 (실제 환경에서는 DB 또는 Redis 사용)
_parse_jobs = {}


def run_parsing_pipeline(
    job_id: str,
    exam_id: str,
    question_pdf: str,
    answer_pdf: Optional[str],
    solution_pdf: Optional[str]
):
    """파싱 파이프라인 실행 (백그라운드)"""
    try:
        _parse_jobs[job_id]["status"] = "processing"
        _parse_jobs[job_id]["progress"] = 10

        # 파이프라인 실행
        cmd = [
            "timeout", "1200",  # 20분 타임아웃
            "python3", "src/teacher/parser/pipeline.py",
            f"input/{exam_id}",
            exam_id,
            "--taxonomy", "src/teacher/taxonomy.yaml",
            "--parser-mode", "vlm",
            "--out", f"output/problems_{exam_id}.json",
            "--fig-out", f"output/figures_{exam_id}.json",
            "--tbl-out", f"output/tables_{exam_id}.json",
            "--bbox-padding", "0.02"
        ]

        # annotated PDF가 있으면 추가
        annotated_pdf = Path(f"output/bbox/question_{exam_id}_annotated.pdf")
        if annotated_pdf.exists():
            cmd.extend(["--annotated-pdf", annotated_pdf.as_posix()])

        _parse_jobs[job_id]["progress"] = 30

        # 실행
        result = subprocess.run(
            cmd,
            cwd="/home/sh/projects/ClassMate",
            capture_output=True,
            text=True,
            timeout=1200
        )

        _parse_jobs[job_id]["progress"] = 90

        if result.returncode == 0:
            # 파싱 성공 - 결과 파일 읽기
            try:
                problems_file = Path(f"/home/sh/projects/ClassMate/output/problems_{exam_id}.json")
                figures_file = Path(f"/home/sh/projects/ClassMate/output/figures_{exam_id}.json")
                tables_file = Path(f"/home/sh/projects/ClassMate/output/tables_{exam_id}.json")

                results = {}
                if problems_file.exists():
                    with open(problems_file, "r", encoding="utf-8") as f:
                        problems = json.load(f)
                        results["problems"] = {
                            "count": len(problems),
                            "file": problems_file.as_posix()
                        }

                if figures_file.exists():
                    with open(figures_file, "r", encoding="utf-8") as f:
                        figures = json.load(f)
                        results["figures"] = {
                            "count": len(figures),
                            "file": figures_file.as_posix()
                        }

                if tables_file.exists():
                    with open(tables_file, "r", encoding="utf-8") as f:
                        tables = json.load(f)
                        results["tables"] = {
                            "count": len(tables),
                            "file": tables_file.as_posix()
                        }

                _parse_jobs[job_id]["results"] = results
                _parse_jobs[job_id]["progress"] = 95
                _parse_jobs[job_id]["message"] = "파싱 완료, DB 업로드 중..."

            except Exception as e:
                print(f"결과 파일 읽기 실패: {e}")
                _parse_jobs[job_id]["status"] = "completed"
                _parse_jobs[job_id]["progress"] = 100
                _parse_jobs[job_id]["message"] = "파싱 완료 (결과 파일 읽기 실패)"
                return

            # 자동 DB 업로드 (Qwen3 임베딩 + Neo4j 저장)
            try:
                print(f"🔄 Starting automatic DB upload for {exam_id}...")

                upload_cmd = [
                    "python3", "src/teacher/parser/upload_problems.py",
                    f"output/problems_{exam_id}.json",
                    "--batch-size", "16"
                ]

                # 임베딩 + DB 업로드 실행 (타임아웃 30분)
                upload_result = subprocess.run(
                    upload_cmd,
                    cwd="/home/sh/projects/ClassMate",
                    capture_output=True,
                    text=True,
                    timeout=1800
                )

                if upload_result.returncode == 0:
                    _parse_jobs[job_id]["status"] = "completed"
                    _parse_jobs[job_id]["progress"] = 100
                    _parse_jobs[job_id]["message"] = "파싱 및 DB 업로드 완료"
                    print(f"✅ DB upload successful for {exam_id}")
                else:
                    _parse_jobs[job_id]["status"] = "completed"
                    _parse_jobs[job_id]["progress"] = 100
                    _parse_jobs[job_id]["message"] = "파싱 완료, DB 업로드 실패"
                    _parse_jobs[job_id]["upload_error"] = upload_result.stderr
                    print(f"⚠️ DB upload failed: {upload_result.stderr}")

            except subprocess.TimeoutExpired:
                _parse_jobs[job_id]["status"] = "completed"
                _parse_jobs[job_id]["progress"] = 100
                _parse_jobs[job_id]["message"] = "파싱 완료, DB 업로드 타임아웃"
                print(f"⚠️ DB upload timeout for {exam_id}")

            except Exception as e:
                _parse_jobs[job_id]["status"] = "completed"
                _parse_jobs[job_id]["progress"] = 100
                _parse_jobs[job_id]["message"] = f"파싱 완료, DB 업로드 오류: {str(e)}"
                print(f"⚠️ DB upload error: {e}")

        else:
            # 실패
            _parse_jobs[job_id]["status"] = "failed"
            _parse_jobs[job_id]["progress"] = 0
            _parse_jobs[job_id]["message"] = "파싱 실패"
            _parse_jobs[job_id]["error"] = result.stderr

    except subprocess.TimeoutExpired:
        _parse_jobs[job_id]["status"] = "failed"
        _parse_jobs[job_id]["message"] = "파싱 타임아웃 (20분 초과)"
        _parse_jobs[job_id]["error"] = "Timeout after 20 minutes"

    except Exception as e:
        _parse_jobs[job_id]["status"] = "failed"
        _parse_jobs[job_id]["message"] = f"파싱 오류: {str(e)}"
        _parse_jobs[job_id]["error"] = str(e)


@router.post("/upload", response_model=ParseJobResponse)
async def upload_exam_files(
    background_tasks: BackgroundTasks,
    exam_id: str = Form(...),
    question_file: UploadFile = File(...),
    answer_file: Optional[UploadFile] = File(None),
    solution_file: Optional[UploadFile] = File(None)
):
    """
    시험지 파일 업로드 및 파싱 시작

    Args:
        exam_id: 시험 ID (예: 2026_09_mock)
        question_file: 문제지 PDF/PNG
        answer_file: 정답지 PDF/PNG (선택)
        solution_file: 해설지 PDF/PNG (선택)

    Returns:
        파싱 작업 정보
    """
    # 작업 ID 생성
    job_id = f"{exam_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 입력 폴더 생성
    input_dir = Path(f"/home/sh/projects/ClassMate/input/{exam_id}")
    input_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = {}

    try:
        # 1. 문제지 저장
        question_path = input_dir / f"question_{exam_id}.pdf"
        with open(question_path, "wb") as f:
            shutil.copyfileobj(question_file.file, f)
        uploaded_files["question"] = question_path.as_posix()

        # 2. 정답지 저장 (선택)
        answer_path = None
        if answer_file:
            answer_path = input_dir / f"answer_{exam_id}.pdf"
            with open(answer_path, "wb") as f:
                shutil.copyfileobj(answer_file.file, f)
            uploaded_files["answer"] = answer_path.as_posix()

        # 3. 해설지 저장 (선택)
        solution_path = None
        if solution_file:
            solution_path = input_dir / f"solution_{exam_id}.pdf"
            with open(solution_path, "wb") as f:
                shutil.copyfileobj(solution_file.file, f)
            uploaded_files["solution"] = solution_path.as_posix()

        # 작업 정보 저장
        _parse_jobs[job_id] = {
            "job_id": job_id,
            "exam_id": exam_id,
            "status": "queued",
            "progress": 0,
            "message": "파싱 대기 중",
            "files": uploaded_files,
            "created_at": datetime.now().isoformat()
        }

        # 백그라운드에서 파싱 시작
        background_tasks.add_task(
            run_parsing_pipeline,
            job_id,
            exam_id,
            question_path.as_posix(),
            answer_path.as_posix() if answer_path else None,
            solution_path.as_posix() if solution_path else None
        )

        return ParseJobResponse(
            job_id=job_id,
            exam_id=exam_id,
            status="queued",
            message="파싱 작업이 시작되었습니다.",
            files=uploaded_files
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")


@router.get("/parse-status/{job_id}", response_model=ParseStatusResponse)
async def get_parse_status(job_id: str):
    """
    파싱 작업 상태 조회

    Args:
        job_id: 작업 ID

    Returns:
        작업 상태 정보
    """
    if job_id not in _parse_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    job = _parse_jobs[job_id]

    return ParseStatusResponse(
        job_id=job_id,
        status=job["status"],
        message=job.get("message", ""),
        progress=job.get("progress", 0),
        results=job.get("results"),
        error=job.get("error")
    )


@router.get("/parse-jobs")
async def list_parse_jobs():
    """
    모든 파싱 작업 목록 조회

    Returns:
        작업 목록
    """
    return {
        "jobs": [
            {
                "job_id": job["job_id"],
                "exam_id": job["exam_id"],
                "status": job["status"],
                "progress": job.get("progress", 0),
                "created_at": job.get("created_at")
            }
            for job in _parse_jobs.values()
        ]
    }


# ==================== Daily Input 관련 ====================

class DailyInputModel(BaseModel):
    """Daily Input 모델 (카테고리는 GPT가 자동 추론)"""
    student_id: str
    date: str  # YYYY-MM-DD
    content: str


class DailyInputResponse(BaseModel):
    """Daily Input 응답"""
    input_id: str
    student_id: str
    student_name: str
    date: str
    content: str
    teacher_id: str
    created_at: str
    summary: Optional[str] = None  # GPT 생성 요약


@router.post("/daily-input")
async def create_daily_input(
    input_data: DailyInputModel,
    teacher_id: str = Form(...),
):
    """
    Daily Input 생성

    Args:
        input_data: Daily Input 데이터
        teacher_id: 선생님 ID

    Returns:
        생성된 Daily Input 정보
    """
    neo4j = Neo4jService.get_instance()

    try:
        # Input ID 생성
        input_id = f"{input_data.student_id}_{input_data.date}_{datetime.now().strftime('%H%M%S')}"

        # Neo4j에 저장 (카테고리 제거, GPT가 자동으로 주제 추론)
        result = neo4j.create_daily_input(
            input_id=input_id,
            student_id=input_data.student_id,
            date=input_data.date,
            content=input_data.content,
            teacher_id=teacher_id
        )

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create daily input")

        return {
            "success": True,
            "input_id": input_id,
            "message": "Daily input created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create daily input: {str(e)}")


@router.get("/daily-inputs/{student_id}")
async def get_student_daily_inputs(
    student_id: str,
    limit: int = 30
):
    """
    학생의 Daily Input 목록 조회

    Args:
        student_id: 학생 ID
        limit: 조회 개수

    Returns:
        Daily Input 목록
    """
    neo4j = Neo4jService.get_instance()

    try:
        inputs = neo4j.get_student_daily_inputs(student_id, limit)
        return {
            "student_id": student_id,
            "inputs": inputs,
            "total": len(inputs)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch daily inputs: {str(e)}")


@router.get("/my-students/{teacher_id}")
async def get_teacher_students(teacher_id: str):
    """
    선생님의 담당 학생 목록 조회

    Args:
        teacher_id: 선생님 ID

    Returns:
        학생 목록 (선생님의 담당 반 학생만)
    """
    try:
        # teachers.json에서 선생님의 담당 반 조회
        teachers_file = Path("/home/sh/projects/ClassMate/data/json/teachers.json")
        with open(teachers_file, "r", encoding="utf-8") as f:
            teachers_data = json.load(f)

        # 선생님의 담당 반 찾기
        assigned_classes = []
        for teacher in teachers_data:
            if teacher["teacher_id"] == teacher_id:
                assigned_classes = teacher["assigned_classes"]
                break

        if not assigned_classes:
            print(f"⚠️ Teacher {teacher_id} has no assigned classes")
            return {
                "teacher_id": teacher_id,
                "students": [],
                "total": 0,
                "assigned_classes": []
            }

        # students_rag.json에서 학생 목록 읽기
        students_file = Path("/home/sh/projects/ClassMate/data/json/students_rag.json")
        with open(students_file, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        # 선생님의 반 학생들만 필터링
        students = [
            {
                "student_id": s["원본데이터"]["student_id"],
                "name": s["원본데이터"]["name"],
                "grade_code": s["원본데이터"]["grade_code"],
                "grade_label": s["원본데이터"]["grade_label"],
                "cefr": s["원본데이터"]["assessment"]["overall"]["cefr"],
                "class_id": s["원본데이터"]["class_id"]
            }
            for s in students_data
            if s["원본데이터"]["class_id"] in assigned_classes
        ]

        return {
            "teacher_id": teacher_id,
            "students": students,
            "total": len(students),
            "assigned_classes": assigned_classes
        }

    except Exception as e:
        print(f"⚠️ Failed to fetch teacher students: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch students: {str(e)}")


# ==================== 학생 정보 업데이트 API ====================

class AttendanceUpdate(BaseModel):
    """출석 정보 업데이트"""
    total_sessions: Optional[int] = None
    absent: Optional[int] = None
    perception: Optional[int] = None  # 지각


class HomeworkUpdate(BaseModel):
    """숙제 정보 업데이트"""
    assigned: Optional[int] = None
    missed: Optional[int] = None


class NotesUpdate(BaseModel):
    """특이사항 업데이트"""
    attitude: Optional[str] = None
    school_exam_level: Optional[str] = None
    csat_level: Optional[str] = None


class RadarScoresUpdate(BaseModel):
    """영역별 점수 업데이트"""
    grammar: Optional[float] = None
    vocabulary: Optional[float] = None
    reading: Optional[float] = None
    listening: Optional[float] = None
    writing: Optional[float] = None


class StudentRecordUpdate(BaseModel):
    """학생 기록 업데이트"""
    attendance: Optional[AttendanceUpdate] = None
    homework: Optional[HomeworkUpdate] = None
    notes: Optional[NotesUpdate] = None
    radar_scores: Optional[RadarScoresUpdate] = None


@router.patch("/student-record/{student_id}")
async def update_student_record(
    student_id: str,
    update_data: StudentRecordUpdate,
    teacher_id: Optional[str] = None  # 선생님 ID (권한 체크용)
):
    """
    학생 기록 업데이트

    Args:
        student_id: 학생 ID
        update_data: 업데이트할 데이터
        teacher_id: 선생님 ID (선택, 권한 체크 시 사용)

    Returns:
        업데이트 결과
    """
    try:
        students_file = Path("/home/sh/projects/ClassMate/data/json/students_rag.json")

        # 파일 읽기
        with open(students_file, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        # teacher_id가 제공된 경우 권한 체크
        if teacher_id:
            teachers_file = Path("/home/sh/projects/ClassMate/data/json/teachers.json")
            with open(teachers_file, "r", encoding="utf-8") as f:
                teachers_data = json.load(f)

            # 선생님의 담당 반 찾기
            assigned_classes = []
            for teacher in teachers_data:
                if teacher["teacher_id"] == teacher_id:
                    assigned_classes = teacher["assigned_classes"]
                    break

            # 학생의 반 확인
            student_class = None
            for student in students_data:
                if student["원본데이터"]["student_id"] == student_id:
                    student_class = student["원본데이터"]["class_id"]
                    break

            # 권한 체크
            if student_class and student_class not in assigned_classes:
                raise HTTPException(
                    status_code=403,
                    detail=f"권한 없음: 선생님 {teacher_id}는 반 {student_class}의 학생을 수정할 수 없습니다."
                )

        # 해당 학생 찾기
        student_found = False
        for student in students_data:
            if student["원본데이터"]["student_id"] == student_id:
                student_found = True
                original_data = student["원본데이터"]

                # 출석 정보 업데이트
                if update_data.attendance:
                    if update_data.attendance.total_sessions is not None:
                        original_data["attendance"]["total_sessions"] = update_data.attendance.total_sessions
                    if update_data.attendance.absent is not None:
                        original_data["attendance"]["absent"] = update_data.attendance.absent
                    if update_data.attendance.perception is not None:
                        original_data["attendance"]["perception"] = update_data.attendance.perception

                # 숙제 정보 업데이트
                if update_data.homework:
                    if update_data.homework.assigned is not None:
                        original_data["homework"]["assigned"] = update_data.homework.assigned
                    if update_data.homework.missed is not None:
                        original_data["homework"]["missed"] = update_data.homework.missed

                # 특이사항 업데이트
                if update_data.notes:
                    if update_data.notes.attitude is not None:
                        original_data["notes"]["attitude"] = update_data.notes.attitude
                    if update_data.notes.school_exam_level is not None:
                        original_data["notes"]["school_exam_level"] = update_data.notes.school_exam_level
                    if update_data.notes.csat_level is not None:
                        original_data["notes"]["csat_level"] = update_data.notes.csat_level

                # 영역별 점수 업데이트 (시계열 이력 저장)
                if update_data.radar_scores:
                    # score_history 배열이 없으면 생성
                    if "score_history" not in original_data["assessment"]:
                        original_data["assessment"]["score_history"] = []

                    # 현재 radar_scores를 history에 추가 (날짜와 함께)
                    current_scores = original_data["assessment"]["radar_scores"].copy()
                    history_entry = {
                        "date": date.today().isoformat(),
                        "scores": current_scores,
                        "teacher_id": teacher_id if teacher_id else "unknown"
                    }
                    original_data["assessment"]["score_history"].append(history_entry)

                    # 최대 90개까지만 유지 (초과 시 가장 오래된 것 제거)
                    if len(original_data["assessment"]["score_history"]) > 90:
                        original_data["assessment"]["score_history"].pop(0)  # 가장 오래된 것 제거

                    # 현재 radar_scores 업데이트
                    if update_data.radar_scores.grammar is not None:
                        original_data["assessment"]["radar_scores"]["grammar"] = update_data.radar_scores.grammar
                    if update_data.radar_scores.vocabulary is not None:
                        original_data["assessment"]["radar_scores"]["vocabulary"] = update_data.radar_scores.vocabulary
                    if update_data.radar_scores.reading is not None:
                        original_data["assessment"]["radar_scores"]["reading"] = update_data.radar_scores.reading
                    if update_data.radar_scores.listening is not None:
                        original_data["assessment"]["radar_scores"]["listening"] = update_data.radar_scores.listening
                    if update_data.radar_scores.writing is not None:
                        original_data["assessment"]["radar_scores"]["writing"] = update_data.radar_scores.writing

                # updated_at 갱신
                original_data["updated_at"] = date.today().isoformat()

                # 자연어 요약 재생성
                print(f"[INFO] Regenerating summary for student {student_id}")
                new_summary = generate_student_summary(original_data)
                student["자연어요약"] = new_summary
                print(f"[INFO] New summary: {new_summary}")

                break

        if not student_found:
            raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

        # 파일 저장
        with open(students_file, "w", encoding="utf-8") as f:
            json.dump(students_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "message": "학생 기록이 업데이트되었습니다.",
            "student_id": student_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기록 업데이트 실패: {str(e)}")


@router.get("/student-detail/{student_id}")
async def get_student_detail(student_id: str):
    """
    학생 상세 정보 조회

    Args:
        student_id: 학생 ID

    Returns:
        학생 상세 정보
    """
    try:
        students_file = Path("/home/sh/projects/ClassMate/data/json/students_rag.json")

        with open(students_file, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        for student in students_data:
            if student["원본데이터"]["student_id"] == student_id:
                return {
                    "success": True,
                    "student": student["원본데이터"]
                }

        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"학생 정보 조회 실패: {str(e)}")


# ==================== Class Schedule 관련 ====================

class ClassScheduleUpdate(BaseModel):
    """Class schedule 업데이트"""
    date: str  # YYYY-MM-DD
    progress: Optional[str] = None  # 수업 진도
    homework: Optional[str] = None  # 숙제
    monthly_test: Optional[str] = None  # 월간 테스트 (월별로 저장)


@router.patch("/class-schedule/{class_id}")
async def update_class_schedule(
    class_id: str,
    update_data: ClassScheduleUpdate,
    teacher_id: Optional[str] = None  # 선생님 ID (권한 체크용)
):
    """
    Class schedule 업데이트 (progress, homework, monthly_test)

    Args:
        class_id: 반 ID
        update_data: 업데이트할 데이터
        teacher_id: 선생님 ID (권한 체크용)

    Returns:
        업데이트 결과
    """
    try:
        # 1. 권한 체크 (선생님이 해당 반 담당인지 확인)
        if teacher_id:
            teachers_file = Path("/home/sh/projects/ClassMate/data/json/teachers.json")
            with open(teachers_file, "r", encoding="utf-8") as f:
                teachers_data = json.load(f)

            assigned_classes = []
            for teacher in teachers_data:
                if teacher["teacher_id"] == teacher_id:
                    assigned_classes = teacher["assigned_classes"]
                    break

            if class_id not in assigned_classes:
                raise HTTPException(
                    status_code=403,
                    detail=f"권한 없음: 선생님 {teacher_id}는 반 {class_id}의 스케줄을 수정할 수 없습니다."
                )

        # 2. class.json 파일 업데이트
        class_file = Path("/home/sh/projects/ClassMate/data/json/class.json")
        with open(class_file, "r", encoding="utf-8") as f:
            class_data = json.load(f)

        class_found = False
        for cls in class_data:
            if cls["class_id"] == class_id:
                class_found = True

                # 필드 업데이트
                if update_data.progress is not None:
                    cls["progress"] = update_data.progress
                if update_data.homework is not None:
                    cls["homework"] = update_data.homework
                if update_data.monthly_test is not None:
                    cls["monthly_test"] = update_data.monthly_test

                # updated_at 갱신
                from datetime import datetime
                cls["updated_at"] = datetime.now().isoformat()

                break

        if not class_found:
            raise HTTPException(status_code=404, detail=f"반 {class_id}를 찾을 수 없습니다.")

        # class.json 저장
        with open(class_file, "w", encoding="utf-8") as f:
            json.dump(class_data, f, ensure_ascii=False, indent=2)

        # 3. 임베딩 생성 (progress + homework + monthly_test 조합)
        current_class = next(c for c in class_data if c["class_id"] == class_id)
        embedding_text = f"반 {class_id} {current_class.get('class_name', '')}: 진도 {current_class.get('progress', '')} | 숙제 {current_class.get('homework', '')} | 월간테스트 {current_class.get('monthly_test', '')}"

        from teacher.shared.embeddings import embed_text
        embedding = embed_text(embedding_text)

        # 4. Neo4j 업데이트
        neo4j = Neo4jService.get_instance()
        with neo4j.get_session() as session:
            session.run("""
                MATCH (c:Class {class_id: $class_id})
                SET c.progress = $progress,
                    c.homework = $homework,
                    c.monthly_test = $monthly_test,
                    c.updated_at = $updated_at,
                    c.embedding = $embedding,
                    c.embedding_ts = datetime()
                RETURN c
            """,
                class_id=class_id,
                progress=current_class.get("progress"),
                homework=current_class.get("homework"),
                monthly_test=current_class.get("monthly_test"),
                updated_at=current_class.get("updated_at"),
                embedding=embedding
            )

        print(f"[INFO] Class {class_id} schedule updated successfully")

        return {
            "success": True,
            "message": "반 스케줄이 업데이트되었습니다.",
            "class_id": class_id,
            "updated_at": current_class.get("updated_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"스케줄 업데이트 실패: {str(e)}")


@router.get("/class-schedule/{class_id}")
async def get_class_schedule(class_id: str):
    """
    Class schedule 조회

    Args:
        class_id: 반 ID

    Returns:
        반 스케줄 정보
    """
    try:
        class_file = Path("/home/sh/projects/ClassMate/data/json/class.json")
        with open(class_file, "r", encoding="utf-8") as f:
            class_data = json.load(f)

        for cls in class_data:
            if cls["class_id"] == class_id:
                return {
                    "success": True,
                    "class": cls
                }

        raise HTTPException(status_code=404, detail=f"반 {class_id}를 찾을 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스케줄 조회 실패: {str(e)}")
