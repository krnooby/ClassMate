# -*- coding: utf-8 -*-
"""
Student data processor for ClassMate daily input
Loads students_rag.json and prepares data for embedding + Neo4j upload
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def load_students_rag(json_path: str) -> List[Dict[str, Any]]:
    """
    Load students_rag.json file

    Args:
        json_path: Path to students_rag.json

    Returns:
        List of student records with "자연어요약" and "원본데이터"
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_student_summary(student: Dict[str, Any]) -> str:
    """
    Extract the natural language summary for embedding

    Args:
        student: Student record with "자연어요약" and "원본데이터"

    Returns:
        Natural language summary text
    """
    return student.get("자연어요약", "")


def extract_student_data(student: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the original student data

    Args:
        student: Student record with "자연어요약" and "원본데이터"

    Returns:
        Original student data dictionary
    """
    return student.get("원본데이터", {})


def prepare_for_neo4j(student: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare student data for Neo4j upload
    Flattens nested structure for easier property access

    Args:
        student: Student record with "자연어요약" and "원본데이터"

    Returns:
        Flattened student data ready for Neo4j
    """
    data = extract_student_data(student)
    summary = extract_student_summary(student)

    # Flatten nested structures
    result = {
        "student_id": data.get("student_id"),
        "name": data.get("name"),
        "class_id": data.get("class_id"),
        "grade_code": data.get("grade_code"),
        "grade_label": data.get("grade_label"),
        "updated_at": data.get("updated_at"),
        "summary": summary,  # For embedding

        # Attendance
        "total_sessions": data.get("attendance", {}).get("total_sessions"),
        "absent": data.get("attendance", {}).get("absent"),
        "perception": data.get("attendance", {}).get("perception"),
        "attendance_rate": None,  # Will calculate below

        # Homework
        "homework_assigned": data.get("homework", {}).get("assigned"),
        "homework_missed": data.get("homework", {}).get("missed"),
        "homework_completion_rate": None,  # Will calculate below

        # Notes
        "attitude": data.get("notes", {}).get("attitude"),
        "school_exam_level": data.get("notes", {}).get("school_exam_level"),
        "csat_level": data.get("notes", {}).get("csat_level"),

        # Assessment
        "cefr": data.get("assessment", {}).get("overall", {}).get("cefr"),
        "percentile_rank": data.get("assessment", {}).get("overall", {}).get("percentile_rank"),

        # Radar scores (individual skills)
        "grammar_score": data.get("assessment", {}).get("radar_scores", {}).get("grammar"),
        "vocabulary_score": data.get("assessment", {}).get("radar_scores", {}).get("vocabulary"),
        "reading_score": data.get("assessment", {}).get("radar_scores", {}).get("reading"),
        "listening_score": data.get("assessment", {}).get("radar_scores", {}).get("listening"),
        "writing_score": data.get("assessment", {}).get("radar_scores", {}).get("writing"),

        # Peer distribution (store as JSON string)
        "peer_distribution": json.dumps(data.get("assessment", {}).get("peer_level_distribution", {})),
    }

    # Calculate rates
    if result["total_sessions"] and result["total_sessions"] > 0:
        attended = result["total_sessions"] - (result["absent"] or 0)
        result["attendance_rate"] = round(attended / result["total_sessions"] * 100, 1)

    if result["homework_assigned"] and result["homework_assigned"] > 0:
        completed = result["homework_assigned"] - (result["homework_missed"] or 0)
        result["homework_completion_rate"] = round(completed / result["homework_assigned"] * 100, 1)

    return result


def batch_prepare_students(json_path: str) -> List[Dict[str, Any]]:
    """
    Load and prepare all students from students_rag.json

    Args:
        json_path: Path to students_rag.json

    Returns:
        List of flattened student data ready for Neo4j
    """
    students = load_students_rag(json_path)
    return [prepare_for_neo4j(s) for s in students]


if __name__ == "__main__":
    # Test the processor
    import argparse

    ap = argparse.ArgumentParser(description="Test student data processor")
    ap.add_argument("json_path", help="Path to students_rag.json")
    args = ap.parse_args()

    students = batch_prepare_students(args.json_path)
    print(f"Loaded {len(students)} students")

    # Show first student as example
    if students:
        print(f"\nFirst student:")
        print(json.dumps(students[0], ensure_ascii=False, indent=2))
