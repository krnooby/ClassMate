# -*- coding: utf-8 -*-
"""
Upload student data to Neo4j with embeddings
Based on students_rag.json format
"""
from __future__ import annotations
import sys
from pathlib import Path

# Add src directory to path
SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import os
import argparse
from typing import List, Dict, Any, Optional

from neo4j import GraphDatabase
from dotenv import load_dotenv

# Import from shared modules
from teacher.shared.embeddings import embed_text, embed_batch

# Import from daily modules
from teacher.daily.student_processor import batch_prepare_students

load_dotenv()

URI   = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
USER  = os.getenv("NEO4J_USERNAME", "neo4j")
PWD   = os.getenv("NEO4J_PASSWORD", "password")
DB    = os.getenv("NEO4J_DB", "neo4j")


# ============================================================
# Cypher Queries
# ============================================================

STUDENT_UPSERT_WITH_EMBEDDING = """
MERGE (s:Student {student_id: $student_id})
SET
  s.name = $name,
  s.class_id = $class_id,
  s.grade_code = $grade_code,
  s.grade_label = $grade_label,
  s.updated_at = $updated_at,
  s.summary = $summary,

  s.total_sessions = $total_sessions,
  s.absent = $absent,
  s.perception = $perception,
  s.attendance_rate = $attendance_rate,

  s.homework_assigned = $homework_assigned,
  s.homework_missed = $homework_missed,
  s.homework_completion_rate = $homework_completion_rate,

  s.attitude = $attitude,
  s.school_exam_level = $school_exam_level,
  s.csat_level = $csat_level,

  s.cefr = $cefr,
  s.percentile_rank = $percentile_rank,

  s.grammar_score = $grammar_score,
  s.vocabulary_score = $vocabulary_score,
  s.reading_score = $reading_score,
  s.listening_score = $listening_score,
  s.writing_score = $writing_score,

  s.peer_distribution = $peer_distribution

FOREACH (_ IN CASE WHEN $student_embedding IS NOT NULL THEN [1] ELSE [] END |
    SET s.student_embedding = $student_embedding)

RETURN s.student_id as student_id, s.name as name
"""

CREATE_STUDENT_VECTOR_INDEX = """
CREATE VECTOR INDEX student_search_index IF NOT EXISTS
FOR (s:Student)
ON s.student_embedding
OPTIONS {indexConfig: {
 `vector.dimensions`: 768,
 `vector.similarity_function`: 'cosine'
}}
"""


# ============================================================
# Neo4j Upload Functions
# ============================================================

def initialize_student_schema(driver):
    """Create vector index for student embeddings"""
    with driver.session(database=DB) as sess:
        try:
            sess.run(CREATE_STUDENT_VECTOR_INDEX)
            print("[info] Student vector index created/verified")
        except Exception as e:
            print(f"[warn] Vector index creation failed (may already exist): {e}")


def upload_student_with_embedding(
    sess,
    student: Dict[str, Any],
    embedding: Optional[List[float]] = None
):
    """
    Upload a single student to Neo4j with embedding

    Args:
        sess: Neo4j session
        student: Student data dict
        embedding: 768D embedding vector (optional)
    """
    params = student.copy()
    params["student_embedding"] = embedding

    result = sess.run(STUDENT_UPSERT_WITH_EMBEDDING, params)
    record = result.single()
    if record:
        print(f"[ok] Uploaded student: {record['student_id']} ({record['name']})")
    else:
        print(f"[warn] No result for student: {student.get('student_id')}")


def upload_students_batch(
    driver,
    students: List[Dict[str, Any]],
    skip_embedding: bool = False
):
    """
    Upload multiple students to Neo4j with embeddings

    Args:
        driver: Neo4j driver
        students: List of student data dicts
        skip_embedding: If True, skip embedding generation (faster for testing)
    """
    print(f"\n{'='*60}")
    print(f"Uploading {len(students)} students to Neo4j")
    print(f"Skip embedding: {skip_embedding}")
    print(f"{'='*60}\n")

    # Generate embeddings in batch if needed
    embeddings: Dict[str, List[float]] = {}
    if not skip_embedding:
        print("[info] Generating embeddings...")
        summaries = [(s["student_id"], s.get("summary", "")) for s in students]
        valid_summaries = [(sid, txt) for sid, txt in summaries if txt.strip()]

        if valid_summaries:
            texts = [txt for _, txt in valid_summaries]
            emb_results = embed_batch(texts)

            for (sid, _), emb in zip(valid_summaries, emb_results):
                embeddings[sid] = emb

            print(f"[ok] Generated {len(embeddings)} embeddings")
        else:
            print("[warn] No valid summaries found for embedding")

    # Upload students one by one
    with driver.session(database=DB) as sess:
        for idx, student in enumerate(students, 1):
            student_id = student.get("student_id")
            embedding = embeddings.get(student_id) if not skip_embedding else None

            try:
                upload_student_with_embedding(sess, student, embedding)
            except Exception as e:
                print(f"[error] Failed to upload {student_id}: {e}")

            if idx % 10 == 0:
                print(f"[progress] {idx}/{len(students)} students uploaded")

    print(f"\n{'='*60}")
    print(f"Upload complete: {len(students)} students")
    print(f"{'='*60}\n")


def verify_students(driver):
    """Verify uploaded student data"""
    with driver.session(database=DB) as sess:
        # Count students
        result = sess.run("MATCH (s:Student) RETURN count(s) as cnt")
        cnt = result.single()["cnt"]
        print(f"[info] Total students in DB: {cnt}")

        # Check embeddings
        result = sess.run("""
            MATCH (s:Student)
            WHERE s.student_embedding IS NOT NULL
            RETURN count(s) as cnt
        """)
        emb_cnt = result.single()["cnt"]
        print(f"[info] Students with embeddings: {emb_cnt}")

        # Sample student
        result = sess.run("""
            MATCH (s:Student)
            RETURN s.student_id, s.name, s.grade_label, s.cefr, s.percentile_rank
            LIMIT 1
        """)
        record = result.single()
        if record:
            print(f"\n[example] Student: {record['s.student_id']}")
            print(f"  Name: {record['s.name']}")
            print(f"  Grade: {record['s.grade_label']}")
            print(f"  CEFR: {record['s.cefr']}")
            print(f"  Percentile: {record['s.percentile_rank']}")


def search_similar_students(driver, query_text: str, limit: int = 5):
    """
    Search for similar students using embedding similarity

    Args:
        driver: Neo4j driver
        query_text: Query text to search for
        limit: Number of results to return
    """
    print(f"\n{'='*60}")
    print(f"Searching for students similar to: '{query_text}'")
    print(f"{'='*60}\n")

    # Generate query embedding
    query_embedding = embed_text(query_text)
    if not query_embedding or len(query_embedding) != 768:
        print("[error] Failed to generate query embedding")
        return

    with driver.session(database=DB) as sess:
        try:
            result = sess.run("""
                CALL db.index.vector.queryNodes('student_search_index', $limit, $query_embedding)
                YIELD node, score
                RETURN node.student_id as student_id,
                       node.name as name,
                       node.grade_label as grade,
                       node.cefr as cefr,
                       node.summary as summary,
                       score
                ORDER BY score DESC
            """, limit=limit, query_embedding=query_embedding)

            results = list(result)
            if not results:
                print("[warn] No results found")
                return

            print(f"[ok] Found {len(results)} similar students:\n")
            for idx, record in enumerate(results, 1):
                print(f"{idx}. {record['student_id']} - {record['name']} ({record['grade']})")
                print(f"   CEFR: {record['cefr']} | Similarity: {record['score']:.4f}")
                print(f"   Summary: {record['summary'][:100]}...")
                print()

        except Exception as e:
            print(f"[error] Search failed: {e}")


# ============================================================
# Main
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="Upload students to Neo4j with embeddings")
    ap.add_argument("json_path", nargs="?", help="Path to students_rag.json")
    ap.add_argument("--skip-embedding", action="store_true", help="Skip embedding generation (faster)")
    ap.add_argument("--init-schema", action="store_true", help="Initialize vector indexes")
    ap.add_argument("--verify", action="store_true", help="Verify uploaded data")
    ap.add_argument("--search", type=str, help="Search for similar students")
    args = ap.parse_args()

    driver = GraphDatabase.driver(URI, auth=(USER, PWD))

    try:
        # Initialize schema
        if args.init_schema:
            print("[info] Initializing student schema...")
            initialize_student_schema(driver)

        # Verify only
        if args.verify:
            verify_students(driver)
            return

        # Search only
        if args.search:
            search_similar_students(driver, args.search)
            return

        # Upload students
        if not args.json_path:
            print("[error] json_path required for upload")
            print("Usage: python upload_students.py <json_path> [--skip-embedding] [--init-schema]")
            return

        if not Path(args.json_path).exists():
            print(f"[error] File not found: {args.json_path}")
            return

        # Load and prepare students
        print(f"[info] Loading students from: {args.json_path}")
        students = batch_prepare_students(args.json_path)
        print(f"[ok] Loaded {len(students)} students")

        # Upload
        upload_students_batch(driver, students, skip_embedding=args.skip_embedding)

        # Verify after upload
        print("\n[info] Verifying upload...")
        verify_students(driver)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
