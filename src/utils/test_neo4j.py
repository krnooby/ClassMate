#!/usr/bin/env python3
"""Neo4j 연결 테스트"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DB")

print(f"🔍 Neo4j 연결 테스트...")
print(f"URI: {uri}")
print(f"Database: {database}")

try:
    driver = GraphDatabase.driver(uri, auth=(username, password))

    with driver.session(database=database) as session:
        result = session.run("RETURN 'Hello Neo4j!' as message")
        record = result.single()
        print(f"✅ 연결 성공: {record['message']}")

        # 노드 개수 확인
        result = session.run("MATCH (n) RETURN count(n) as count")
        count = result.single()["count"]
        print(f"📊 총 노드 수: {count}")

        # Student 노드 확인
        result = session.run("MATCH (s:Student) RETURN count(s) as count")
        student_count = result.single()["count"]
        print(f"👨‍🎓 Student 노드 수: {student_count}")

    driver.close()
    print("\n✅ Neo4j 준비 완료!")

except Exception as e:
    print(f"\n❌ 연결 실패: {e}")
    print("\n💡 Neo4j 서버가 실행 중인지 확인하세요.")
