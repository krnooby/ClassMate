# -*- coding: utf-8 -*-
"""
Automated pipeline to upload problems, tables, figures to Neo4j with embeddings
Uses Qwen3-Embedding-0.6B for text embeddings
"""
from __future__ import annotations
import os, sys, json, argparse
from pathlib import Path
from typing import Iterator, Dict, Any, List, Union, Tuple, Optional

# Add src to path
SRC = Path(__file__).resolve().parents[2]  # src/teacher/parser/upload_problems.py -> src/
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neo4j import GraphDatabase
from dotenv import load_dotenv

# Import embedding module
from teacher.shared.embeddings import embed_problem, create_searchable_embedding, embed_batch

load_dotenv()

URI   = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
USER  = os.getenv("NEO4J_USERNAME", "neo4j")
PASS  = os.getenv("NEO4J_PASSWORD", "password")
DB    = os.getenv("NEO4J_DB", "classmate")

driver = GraphDatabase.driver(URI, auth=(USER, PASS))

# ---------- IO ----------

def _iter_json_paths(path: Path) -> List[Path]:
    if path.is_dir():
        return sorted(path.rglob("*.json"))
    if path.suffix.lower() != ".json":
        raise ValueError(f"only .json allowed: {path}")
    return [path]

def _records_from_file(p: Path) -> Iterator[Tuple[str, Dict[str, Any]]]:
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for i, obj in enumerate(data):
            yield (f"{p}#{i}", obj)
    else:
        yield (str(p), data)

def _detect(obj: Dict[str, Any]) -> str:
    if "table_id" in obj: return "tbl"
    if "asset_id" in obj: return "fig"
    return "problem"

# ---------- Enhanced Cypher with Embeddings ----------

PROBLEM_UPSERT_WITH_EMBEDDING = """
MERGE (p:Problem {problem_id: coalesce($problem_id, $item_id)})
ON CREATE SET p._ing = true
SET p.area = coalesce(p.area,$area),
    p.mid_code = coalesce(p.mid_code,$mid_code),
    p.grade_band = coalesce(p.grade_band,$grade_band),
    p.cefr = coalesce(p.cefr,$cefr),
    p.difficulty = coalesce(p.difficulty,toInteger($difficulty)),
    p.type = coalesce(p.type,$type),
    p.stem = coalesce(p.stem,$stem),
    p.answer = coalesce(p.answer,$answer),
    p.rationale = coalesce(p.rationale,$rationale),
    p.figure_ref = coalesce(p.figure_ref,$figure_ref),
    p.table_ref  = coalesce(p.table_ref,$table_ref),
    p.visual_source = coalesce(p.visual_source,$visual_source),
    p.features_json = coalesce(p.features_json,$features_json),
    p.item_no = coalesce(p.item_no, toInteger($item_no))
SET p.options = CASE WHEN $options IS NULL THEN p.options ELSE apoc.coll.toSet(coalesce(p.options,[])+$options) END,
    p.tags    = CASE WHEN $tags    IS NULL THEN p.tags    ELSE apoc.coll.toSet(coalesce(p.tags,[])+$tags) END
FOREACH (_ IN CASE WHEN $audio_transcript IS NULL THEN [] ELSE [1] END | SET p.audio_transcript = coalesce(p.audio_transcript,$audio_transcript))
FOREACH (_ IN CASE WHEN $search_embedding IS NOT NULL THEN [1] ELSE [] END | SET p.search_embedding = $search_embedding)
FOREACH (_ IN CASE WHEN $stem_embedding IS NOT NULL THEN [1] ELSE [] END | SET p.stem_embedding = $stem_embedding)
FOREACH (_ IN CASE WHEN $rationale_embedding IS NOT NULL THEN [1] ELSE [] END | SET p.rationale_embedding = $rationale_embedding)
WITH p
OPTIONAL MATCH (t:Tbl {table_id:p.table_ref})
OPTIONAL MATCH (f:Fig {asset_id:p.figure_ref})
OPTIONAL MATCH (cCand:Curriculum {mid_code:$mid_code})
WITH p,t,f,cCand,
     CASE cCand.area
       WHEN '문법' THEN 'GR'
       WHEN '듣기' THEN 'LS'
       WHEN '독해' THEN 'RD'
       WHEN '어휘' THEN 'VO'
       WHEN '쓰기' THEN 'WR'
       ELSE cCand.area
     END AS c_area_norm
FOREACH (_ IN CASE WHEN t IS NOT NULL THEN [1] ELSE [] END | MERGE (p)-[:HAS_TABLE {role:'question'}]->(t))
FOREACH (_ IN CASE WHEN f IS NOT NULL THEN [1] ELSE [] END | MERGE (p)-[:HAS_FIG   {role:'question'}]->(f))
/* Curriculum → Problem 연결 */
FOREACH (_ IN CASE WHEN cCand IS NOT NULL
                    AND c_area_norm = p.area
                    AND (cCand.cefr IS NULL OR cCand.cefr = p.cefr)
                   THEN [1] ELSE [] END |
  MERGE (cCand)-[r:INCLUDES_PROBLEM]->(p)
  SET r.area = p.area, r.cefr = p.cefr, r.difficulty = p.difficulty, r.type = p.type)
WITH p,
  exists( (p)-[:HAS_TABLE]->(:Tbl {table_id:p.table_ref}) ) AS has_tbl,
  exists( (p)-[:HAS_FIG]->(:Fig  {asset_id:p.figure_ref}) ) AS has_fig,
  exists( (:Curriculum)-[:INCLUDES_PROBLEM]->(p) ) AS has_curr,
  coalesce(p._ing,false) AS created
REMOVE p._ing
RETURN p.problem_id AS id, created, has_tbl, has_fig, has_curr,
       size(p.search_embedding) AS emb_dim;
"""

TBL_UPSERT = """
MERGE (t:Tbl {table_id:$table_id})
ON CREATE SET t._ing = true
SET t.problem_id = coalesce(t.problem_id,$problem_id),
    t.title = coalesce(t.title,$title),
    t.columns = coalesce(t.columns,$columns),
    t.types_json = coalesce(t.types_json,$types_json),
    t.rows_json = coalesce(t.rows_json,$rows_json),
    t.option_row_map_json = coalesce(t.option_row_map_json,$option_row_map_json),
    t.source_json = coalesce(t.source_json,$source_json),
    t.storage_key = coalesce(t.storage_key,$storage_key),
    t.public_url = coalesce(t.public_url,$public_url)
WITH t
OPTIONAL MATCH (p1:Problem {table_ref:t.table_id})
OPTIONAL MATCH (p2:Problem {problem_id:t.problem_id})
WITH t, coalesce(p1,p2) AS p
FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END | MERGE (p)-[:HAS_TABLE {role:'question'}]->(t))
WITH t, coalesce(t._ing,false) AS created
REMOVE t._ing
RETURN t.table_id AS id, created;
"""

FIG_UPSERT = """
MERGE (f:Fig {asset_id:$asset_id})
ON CREATE SET f._ing = true
SET f.problem_id = coalesce(f.problem_id,$problem_id),
    f.asset_type = coalesce(f.asset_type,$asset_type),
    f.storage_key = coalesce(f.storage_key,$storage_key),
    f.public_url = coalesce(f.public_url,$public_url),
    f.mime = coalesce(f.mime,$mime),
    f.page = coalesce(f.page,toInteger($page)),
    f.bbox_norm = coalesce(f.bbox_norm,$bbox_norm),
    f.overlay_text = coalesce(f.overlay_text,$overlay_text),
    f.hash = coalesce(f.hash,$hash),
    f.labels = coalesce(f.labels,$labels),
    f.caption = coalesce(f.caption,$caption)
WITH f
OPTIONAL MATCH (p1:Problem {problem_id:f.problem_id})
OPTIONAL MATCH (p2:Problem {figure_ref:f.asset_id})
WITH f, coalesce(p1,p2) AS p, coalesce(f._ing,false) AS created
FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END | MERGE (p)-[:HAS_FIG {role:'question'}]->(f))
REMOVE f._ing
RETURN f.asset_id AS id, created, (p IS NOT NULL) AS linked;
"""

# ---------- Vector Index Creation ----------

CREATE_VECTOR_INDEX = """
CREATE VECTOR INDEX problem_search_index IF NOT EXISTS
FOR (p:Problem)
ON p.search_embedding
OPTIONS {indexConfig: {
 `vector.dimensions`: 1024,
 `vector.similarity_function`: 'cosine'
}}
"""

CREATE_STEM_VECTOR_INDEX = """
CREATE VECTOR INDEX problem_stem_index IF NOT EXISTS
FOR (p:Problem)
ON p.stem_embedding
OPTIONS {indexConfig: {
 `vector.dimensions`: 1024,
 `vector.similarity_function`: 'cosine'
}}
"""

# ---------- Param builders with embeddings ----------

def params_from_problem(obj: Dict[str, Any], embeddings: Optional[Dict[str, List[float]]] = None) -> Dict[str, Any]:
    """Build parameters including embeddings"""
    feat = obj.get("features")

    # Extract problem number from item_id (e.g., "2026_09_mock-0001" -> 1)
    item_id = obj.get("item_id") or obj.get("problem_id") or ""
    item_no = None
    if "-" in item_id:
        try:
            item_no = int(item_id.split("-")[-1])
        except:
            pass

    if item_no is None:
        item_no = obj.get("no")

    params = {
        "problem_id": obj.get("problem_id") or obj.get("item_id"),
        "item_id": obj.get("item_id"),
        "item_no": item_no,
        "area": obj.get("area"),
        "mid_code": obj.get("mid_code"),
        "grade_band": obj.get("grade_band"),
        "cefr": obj.get("cefr"),
        "difficulty": obj.get("difficulty"),
        "type": obj.get("type"),
        "stem": obj.get("stem"),
        "answer": obj.get("answer"),
        "rationale": obj.get("rationale"),
        "options": obj.get("options"),
        "tags": obj.get("tags"),
        "figure_ref": (feat or {}).get("figure_ref") or obj.get("figure_ref"),
        "table_ref":  (feat or {}).get("table_ref")  or obj.get("table_ref"),
        "visual_source": (feat or {}).get("visual_source") or obj.get("visual_source"),
        "features_json": json.dumps(feat) if feat is not None else None,
        "audio_transcript": obj.get("audio_transcript"),
    }

    # Add embeddings if provided
    if embeddings:
        params["search_embedding"] = embeddings.get("search_embedding")
        params["stem_embedding"] = embeddings.get("stem_embedding")
        params["rationale_embedding"] = embeddings.get("rationale_embedding")
    else:
        params["search_embedding"] = None
        params["stem_embedding"] = None
        params["rationale_embedding"] = None

    return params

def params_from_tbl(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "table_id": obj["table_id"],
        "problem_id": obj.get("problem_id") or obj.get("item_id"),
        "title": obj.get("title"),
        "columns": obj.get("columns") or [],
        "types_json": json.dumps(obj.get("types")) if obj.get("types") is not None else None,
        "rows_json": json.dumps(obj.get("rows")) if obj.get("rows") is not None else None,
        "option_row_map_json": json.dumps(obj.get("option_row_map")) if obj.get("option_row_map") is not None else None,
        "source_json": json.dumps(obj.get("source")) if obj.get("source") is not None else None,
        "storage_key": obj.get("storage_key"),
        "public_url": obj.get("public_url"),
    }

def params_from_fig(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "asset_id": obj["asset_id"],
        "problem_id": obj.get("problem_id") or obj.get("item_id"),
        "asset_type": obj.get("asset_type"),
        "storage_key": obj.get("storage_key"),
        "public_url": obj.get("public_url"),
        "mime": obj.get("mime"),
        "page": obj.get("page"),
        "bbox_norm": obj.get("bbox_norm"),
        "overlay_text": obj.get("overlay_text") or [],
        "hash": obj.get("hash"),
        "labels": obj.get("labels") or [],
        "caption": obj.get("caption"),
    }

# ---------- Upserts with embeddings ----------

def upsert_problem_with_embedding(sess, obj: Dict[str, Any], skip_embedding: bool = False):
    """Upload problem with embeddings"""
    embeddings = None

    if not skip_embedding:
        try:
            print(f"  → Generating embeddings for problem {obj.get('item_id')}...", flush=True)
            # Generate all embeddings
            all_embeddings = embed_problem(obj)
            # Create search embedding
            search_emb = create_searchable_embedding(obj)

            embeddings = {
                "search_embedding": search_emb,
                "stem_embedding": all_embeddings.get("stem_embedding"),
                "rationale_embedding": all_embeddings.get("rationale_embedding"),
            }
        except Exception as e:
            print(f"  ⚠ Embedding generation failed: {e}, continuing without embeddings", flush=True)

    res = sess.run(PROBLEM_UPSERT_WITH_EMBEDDING, **params_from_problem(obj, embeddings)).single()

    emb_info = f"emb_dim={res['emb_dim']}" if res['emb_dim'] else "no_emb"
    print(f"[OK][problem][{res['id']}] {'CREATED' if res['created'] else 'MERGED'} tbl:{int(res['has_tbl'])} fig:{int(res['has_fig'])} curr:{int(res['has_curr'])} {emb_info}", flush=True)

def upsert_tbl(sess, obj: Dict[str, Any]):
    res = sess.run(TBL_UPSERT, **params_from_tbl(obj)).single()
    print(f"[OK][tbl][{res['id']}] {'CREATED' if res['created'] else 'MERGED'}", flush=True)

def upsert_fig(sess, obj: Dict[str, Any]):
    res = sess.run(FIG_UPSERT, **params_from_fig(obj)).single()
    print(f"[OK][fig][{res['id']}] {'CREATED' if res['created'] else 'MERGED'} linked:{int(res['linked'])}", flush=True)

# ---------- Initialize Neo4j schema ----------

def initialize_schema(sess):
    """Create vector indexes and constraints"""
    print("[schema] Creating vector indexes...", flush=True)
    try:
        sess.run(CREATE_VECTOR_INDEX)
        print("  ✓ Created search embedding index", flush=True)
    except Exception as e:
        print(f"  ⚠ Search index: {e}", flush=True)

    try:
        sess.run(CREATE_STEM_VECTOR_INDEX)
        print("  ✓ Created stem embedding index", flush=True)
    except Exception as e:
        print(f"  ⚠ Stem index: {e}", flush=True)

# ---------- Ingest with embeddings ----------

def ingest(path: Union[str, Path], only: str = None, skip_embedding: bool = False, init_schema: bool = False):
    """
    Main ingestion function with embedding support

    Args:
        path: Path to JSON file or directory
        only: Force type detection (problem/tbl/fig)
        skip_embedding: Skip embedding generation (faster for testing)
        init_schema: Initialize vector indexes
    """
    path = Path(path)
    cnt = {"problem": 0, "tbl": 0, "fig": 0}
    err = 0

    with driver.session(database=DB) as sess:
        if init_schema:
            initialize_schema(sess)

        for file_path in _iter_json_paths(path):
            print(f"\n[file] Processing {file_path.name}...", flush=True)
            try:
                for src, obj in _records_from_file(file_path):
                    try:
                        kind = only or _detect(obj)
                        if kind == "problem":
                            upsert_problem_with_embedding(sess, obj, skip_embedding)
                            cnt["problem"] += 1
                        elif kind == "tbl":
                            upsert_tbl(sess, obj)
                            cnt["tbl"] += 1
                        elif kind == "fig":
                            upsert_fig(sess, obj)
                            cnt["fig"] += 1
                        else:
                            raise ValueError(f"unknown record type: {kind}")
                    except Exception as e:
                        err += 1
                        print(f"[ERR] {src}: {e.__class__.__name__}: {e}", file=sys.stderr, flush=True)
            except Exception as e:
                err += 1
                print(f"[ERR] {file_path}: {e.__class__.__name__}: {e}", file=sys.stderr, flush=True)

    print(f"\n=== Summary ===")
    print(f"Problems: {cnt['problem']}")
    print(f"Tables: {cnt['tbl']}")
    print(f"Figures: {cnt['fig']}")
    print(f"Errors: {err}")

# ---------- Verification functions ----------

def verify_relationships(limit: int = 10):
    """Verify uploaded data and relationships"""
    print("\n=== Verifying Neo4j Data ===\n")

    with driver.session(database=DB) as sess:
        # Count nodes
        result = sess.run("""
            MATCH (p:Problem) RETURN count(p) as problems
        """).single()
        print(f"Total Problems: {result['problems']}")

        result = sess.run("""
            MATCH (t:Tbl) RETURN count(t) as tables
        """).single()
        print(f"Total Tables: {result['tables']}")

        result = sess.run("""
            MATCH (f:Fig) RETURN count(f) as figures
        """).single()
        print(f"Total Figures: {result['figures']}")

        # Count relationships
        result = sess.run("""
            MATCH (p:Problem)-[r:HAS_TABLE]->(t:Tbl) RETURN count(r) as rels
        """).single()
        print(f"Problem → Table relationships: {result['rels']}")

        result = sess.run("""
            MATCH (p:Problem)-[r:HAS_FIG]->(f:Fig) RETURN count(r) as rels
        """).single()
        print(f"Problem → Figure relationships: {result['rels']}")

        result = sess.run("""
            MATCH (c:Curriculum)-[r:INCLUDES_PROBLEM]->(p:Problem) RETURN count(r) as rels
        """).single()
        print(f"Curriculum → Problem relationships: {result['rels']}")

        # Check embeddings
        result = sess.run("""
            MATCH (p:Problem) WHERE p.search_embedding IS NOT NULL
            RETURN count(p) as with_emb
        """).single()
        print(f"Problems with embeddings: {result['with_emb']}")

        # Sample problems with relationships
        print(f"\n=== Sample Problems (limit {limit}) ===\n")
        results = sess.run(f"""
            MATCH (p:Problem)
            OPTIONAL MATCH (p)-[:HAS_TABLE]->(t:Tbl)
            OPTIONAL MATCH (p)-[:HAS_FIG]->(f:Fig)
            OPTIONAL MATCH (c:Curriculum)-[:INCLUDES_PROBLEM]->(p)
            RETURN p.problem_id as id, p.item_no as no, p.stem[..50] as stem,
                   t.table_id as table, f.asset_id as figure, c.mid_code as curriculum,
                   size(p.search_embedding) as emb_dim
            ORDER BY p.item_no
            LIMIT {limit}
        """)

        for record in results:
            print(f"[{record['no']:02d}] {record['id']}")
            print(f"     Stem: {record['stem']}...")
            if record['table']:
                print(f"     → Table: {record['table']}")
            if record['figure']:
                print(f"     → Figure: {record['figure']}")
            if record['curriculum']:
                print(f"     → Curriculum: {record['curriculum']}")
            if record['emb_dim']:
                print(f"     → Embedding: {record['emb_dim']}D")
            print()

def search_similar_problems(query_text: str, limit: int = 5):
    """Search for similar problems using vector similarity"""
    from teacher.shared.embeddings import embed_text

    print(f"\n=== Searching for: '{query_text}' ===\n")

    # Generate query embedding
    query_emb = embed_text(query_text)

    with driver.session(database=DB) as sess:
        results = sess.run("""
            CALL db.index.vector.queryNodes('problem_search_index', $limit, $query_embedding)
            YIELD node, score
            RETURN node.problem_id as id, node.item_no as no,
                   node.stem as stem, node.area as area, score
            ORDER BY score DESC
        """, query_embedding=query_emb, limit=limit)

        for i, record in enumerate(results, 1):
            print(f"{i}. [{record['no']:02d}] {record['id']} (score: {record['score']:.4f})")
            print(f"   Area: {record['area']}")
            print(f"   Stem: {record['stem'][:100]}...")
            print()

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Upload problems to Neo4j with embeddings")
    ap.add_argument("path", nargs="?", default="output", help="JSON file or directory")
    ap.add_argument("--type", choices=["problem", "tbl", "fig"], help="force type")
    ap.add_argument("--skip-embedding", action="store_true", help="Skip embedding generation (faster)")
    ap.add_argument("--init-schema", action="store_true", help="Initialize vector indexes")
    ap.add_argument("--verify", action="store_true", help="Verify uploaded data")
    ap.add_argument("--search", type=str, help="Search similar problems")
    args = ap.parse_args()

    try:
        if args.verify:
            verify_relationships()
        elif args.search:
            search_similar_problems(args.search)
        else:
            ingest(args.path, args.type, args.skip_embedding, args.init_schema)

            # Auto-verify after upload
            if not args.skip_embedding:
                verify_relationships(limit=5)
    finally:
        driver.close()

if __name__ == "__main__":
    main()
