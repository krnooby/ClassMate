#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo4j 벡터 인덱스 및 제약조건 설정 스크립트
GraphRAG를 위한 벡터 인덱스와 기타 필요한 인덱스를 생성합니다.
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


def create_indexes(driver, database: str):
    """
    Neo4j 인덱스 및 제약조건 생성

    Args:
        driver: Neo4j 드라이버
        database: 데이터베이스 이름
    """
    with driver.session(database=database) as session:
        print("📊 Neo4j 인덱스 및 제약조건 생성 중...\n")

        # 1. Student 노드 제약조건 (고유 ID)
        print("1️⃣  Student.student_id 고유 제약조건 생성 중...")
        try:
            session.run("""
                CREATE CONSTRAINT student_id_unique IF NOT EXISTS
                FOR (s:Student)
                REQUIRE s.student_id IS UNIQUE
            """)
            print("   ✅ Student.student_id 고유 제약조건 생성 완료")
        except Exception as e:
            print(f"   ⚠️  제약조건이 이미 존재하거나 생성 실패: {e}")

        # 2. 벡터 인덱스 생성 (가장 중요!)
        print("\n2️⃣  Student.embedding 벡터 인덱스 생성 중...")
        try:
            session.run("""
                CREATE VECTOR INDEX student_embedding_index IF NOT EXISTS
                FOR (s:Student)
                ON s.embedding
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """)
            print("   ✅ Student.embedding 벡터 인덱스 생성 완료")
            print("      - 차원: 1536")
            print("      - 유사도 함수: cosine")
        except Exception as e:
            print(f"   ⚠️  벡터 인덱스가 이미 존재하거나 생성 실패: {e}")

        # 3. Student.name 인덱스 (검색용)
        print("\n3️⃣  Student.name 인덱스 생성 중...")
        try:
            session.run("""
                CREATE INDEX student_name_index IF NOT EXISTS
                FOR (s:Student)
                ON (s.name)
            """)
            print("   ✅ Student.name 인덱스 생성 완료")
        except Exception as e:
            print(f"   ⚠️  인덱스가 이미 존재하거나 생성 실패: {e}")

        # 4. Student.cefr 인덱스 (레벨별 검색)
        print("\n4️⃣  Student.cefr 인덱스 생성 중...")
        try:
            session.run("""
                CREATE INDEX student_cefr_index IF NOT EXISTS
                FOR (s:Student)
                ON (s.cefr)
            """)
            print("   ✅ Student.cefr 인덱스 생성 완료")
        except Exception as e:
            print(f"   ⚠️  인덱스가 이미 존재하거나 생성 실패: {e}")

        # 5. Class 노드 제약조건
        print("\n5️⃣  Class.class_id 고유 제약조건 생성 중...")
        try:
            session.run("""
                CREATE CONSTRAINT class_id_unique IF NOT EXISTS
                FOR (c:Class)
                REQUIRE c.class_id IS UNIQUE
            """)
            print("   ✅ Class.class_id 고유 제약조건 생성 완료")
        except Exception as e:
            print(f"   ⚠️  제약조건이 이미 존재하거나 생성 실패: {e}")

        # 6. Teacher 노드 제약조건
        print("\n6️⃣  Teacher.teacher_id 고유 제약조건 생성 중...")
        try:
            session.run("""
                CREATE CONSTRAINT teacher_id_unique IF NOT EXISTS
                FOR (t:Teacher)
                REQUIRE t.teacher_id IS UNIQUE
            """)
            print("   ✅ Teacher.teacher_id 고유 제약조건 생성 완료")
        except Exception as e:
            print(f"   ⚠️  제약조건이 이미 존재하거나 생성 실패: {e}")


def verify_indexes(driver, database: str):
    """
    생성된 인덱스 확인

    Args:
        driver: Neo4j 드라이버
        database: 데이터베이스 이름
    """
    with driver.session(database=database) as session:
        print("\n" + "=" * 60)
        print("📋 생성된 인덱스 및 제약조건 확인")
        print("=" * 60)

        # 인덱스 조회
        result = session.run("SHOW INDEXES")
        indexes = list(result)

        if indexes:
            print(f"\n총 {len(indexes)}개의 인덱스:")
            for idx in indexes:
                index_name = idx.get("name", "N/A")
                index_type = idx.get("type", "N/A")
                labels = idx.get("labelsOrTypes", [])
                properties = idx.get("properties", [])

                print(f"\n   📌 {index_name}")
                print(f"      - 타입: {index_type}")
                print(f"      - 레이블: {labels}")
                print(f"      - 속성: {properties}")
        else:
            print("⚠️  인덱스가 없습니다.")

        # 제약조건 조회
        result = session.run("SHOW CONSTRAINTS")
        constraints = list(result)

        if constraints:
            print(f"\n총 {len(constraints)}개의 제약조건:")
            for const in constraints:
                const_name = const.get("name", "N/A")
                const_type = const.get("type", "N/A")
                labels = const.get("labelsOrTypes", [])
                properties = const.get("properties", [])

                print(f"\n   🔒 {const_name}")
                print(f"      - 타입: {const_type}")
                print(f"      - 레이블: {labels}")
                print(f"      - 속성: {properties}")
        else:
            print("⚠️  제약조건이 없습니다.")


def main():
    """메인 실행 함수"""
    # 환경 변수 로드
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DB", "neo4j")

    print("🔍 Neo4j 연결 중...")
    print(f"   URI: {uri}")
    print(f"   Database: {database}")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))

        # 연결 테스트
        with driver.session(database=database) as session:
            result = session.run("RETURN 'Connected!' as message")
            message = result.single()["message"]
            print(f"✅ Neo4j 연결 성공: {message}\n")

        # 인덱스 생성
        create_indexes(driver, database)

        # 인덱스 확인
        verify_indexes(driver, database)

        driver.close()

        print("\n" + "=" * 60)
        print("✅ Neo4j 인덱스 설정 완료!")
        print("=" * 60)

        print("\n💡 다음 단계:")
        print("   1. embed_students.py를 실행하여 임베딩 생성")
        print("   2. upload_student_embeddings.py를 실행하여 데이터 업로드")

    except Exception as e:
        print(f"\n❌ Neo4j 연결 실패: {e}")
        print("\n💡 확인 사항:")
        print("   - Neo4j 서버가 실행 중인가?")
        print("   - .env 파일의 연결 정보가 올바른가?")
        print("   - 네트워크 연결이 가능한가?")


if __name__ == "__main__":
    main()
