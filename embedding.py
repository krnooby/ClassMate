#!/usr/bin/env python3
# neo4j_embed_qwen3.py (with logging; fixed pagination + driver usage)
# pip install torch transformers "neo4j>=5.23.0" python-dotenv tqdm

import os, time, argparse, json, logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from neo4j import GraphDatabase, ManagedTransaction
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired
from dotenv import load_dotenv
from tqdm import tqdm

import torch
from transformers import AutoTokenizer, AutoModel

# ---------- config ----------
DEFAULT_LABELS = [
    "Assessment","Attendance","Class","Curriculum","Fig","Homework","Notes","Parent",
    "PeerDistribution","Problem","RadarScores","Student","Tbl","TblRow","Teacher"
]

FIELD_HINTS = {
    "Problem": ["area","mid_code","grade_band","cefr","difficulty","type","stem","options","answer","rationale","tags","problem_id","features_json"],
    "Student": ["student_id","name","grade_code","grade_label","class_id","자연어요약","원본데이터","assessment","attendance","homework","notes","updated_at"],
    "Assessment": ["cefr","data_json","percentile_rank","student_id"],
    "Attendance": ["absent","perception","student_id","total_sessions"],
    "Homework": ["assigned","missed","student_id"],
    "Class": ["class_id","class_name","class_cefr","class_end_time","class_start_time","teacher_id","homework","monthly_test","progress","schedule","updated_at"],
    "Curriculum": ["mid_code","name_ko","area","teach_note_A","teach_note_B","teach_note_C","teach_note_D","updated_at"],
    "Notes": ["attitude","csat_level","school_exam_level","student_id"],
    "Parent": ["name","phone","raw"],
    "Teacher": ["name","class_name","email","teacher_id"],
    "Tbl": ["table_id","problem_id","title","columns","rows_json","types_json","option_row_map_json","source_json","created_at","updated_at"],
    "TblRow": ["row_index","table_id"],
    "Fig": ["asset_id","problem_id","asset_type","mime","page","bbox_norm","hash","overlay_text","public_url","storage_key","created_at","updated_at"],
    "RadarScores": ["grammar","vocabulary","reading","listening","writing","student_id"],
    "PeerDistribution": ["A1","A2","B1","B2","C1","C2","student_id"],
}

REL_SUMMARY_UPTO = 0   # 각 이웃 라벨 당 최대 요약 수

# ---------- logging ----------
log = logging.getLogger("embed")

# ---------- helpers ----------
def _kv_dump(props: Dict[str, Any], keys: Optional[List[str]] = None) -> str:
    if not props: return ""
    # 임베딩 관련 속성 제외 (순환 참조 방지)
    SKIP_KEYS = {'embedding', 'embedding_model', 'embedding_dim', 'embedding_ts',
                 'search_embedding', 'stem_embedding', 'rationale_embedding', 'student_embedding'}

    out = []
    if keys:
        for k in keys:
            if k in props and k not in SKIP_KEYS:
                v = props[k]
                if isinstance(v, (list, tuple)):
                    v = ", ".join(map(lambda x: str(x), v))
                elif isinstance(v, dict):
                    v = json.dumps(v, ensure_ascii=False)
                out.append(f"{k}: {v}")
    for k, v in props.items():
        if keys and k in keys:
            continue
        if k in SKIP_KEYS:  # 임베딩 속성 스킵
            continue
        if isinstance(v, (list, tuple)):
            v = ", ".join(map(lambda x: str(x), v))
        elif isinstance(v, dict):
            v = json.dumps(v, ensure_ascii=False)
        out.append(f"{k}: {v}")
    return "\n".join(out)

def build_text(label: str, props: Dict[str,Any], rels: Dict[str,List[Dict[str,Any]]]) -> str:
    hints = FIELD_HINTS.get(label)
    self_txt = _kv_dump(props, hints)
    rel_chunks = []
    for rel_name, neigh_list in rels.items():
        if not neigh_list:
            continue
        sample = neigh_list[:REL_SUMMARY_UPTO]
        parts = []
        for n in sample:
            nl = n.get("label","")
            np = n.get("props",{})
            parts.append(f"[{nl}] " + _kv_dump(np, FIELD_HINTS.get(nl, None)).replace("\n","; "))
        rel_chunks.append(f"{rel_name}: " + " | ".join(parts))
    rel_txt = "\n".join(rel_chunks)
    return f"[{label}]\n{self_txt}\n{rel_txt}".strip()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------- Neo4j ----------
def fetch_nodes(tx: ManagedTransaction, label: str, skip: int, limit: int) -> List[Tuple[int, Dict[str,Any]]]:
    q = f"""
    MATCH (n:`{label}`)
    RETURN id(n) AS id, properties(n) AS props
    ORDER BY id(n)
    SKIP $skip LIMIT $limit
    """
    return [(r["id"], r["props"]) for r in tx.run(q, skip=skip, limit=limit)]  # type: ignore

def fetch_rel_summaries(tx: ManagedTransaction, ids: List[int]) -> Dict[int, Dict[str,List[Dict[str,Any]]]]:
    if not ids: return {}
    q = """
    UNWIND $ids AS nid
    MATCH (n) WHERE id(n)=nid
    CALL {
      WITH n
      MATCH (n)-[r]->(m)
      RETURN collect({rel:type(r), label: head(labels(m)), props: properties(m)}) AS outs
    }
    CALL {
      WITH n
      MATCH (m)-[r]->(n)
      RETURN collect({rel:type(r), label: head(labels(m)), props: properties(m)}) AS ins
    }
    WITH nid, outs + ins AS allrels
    UNWIND allrels AS x
    WITH nid, x.rel AS rel, collect({label:x.label, props:x.props}) AS lst
    RETURN nid, collect({rel:rel, lst:lst}) AS rels
    """
    rels: Dict[int, Dict[str,List[Dict[str,Any]]]] = {}
    for rec in tx.run(q, ids=ids):  # type: ignore
        nid = rec["nid"]
        d: Dict[str,List[Dict[str,Any]]] = {}
        for item in rec["rels"]:
            d[item["rel"]] = item["lst"]
        rels[nid] = d
    return rels

def set_embeddings(tx: ManagedTransaction, label: str, rows: List[Tuple[int, List[float], str, int]]):
    q = f"""
    UNWIND $rows AS row
    MATCH (n:`{label}`) WHERE id(n)=row.id
    SET n.embedding = row.vec,
        n.embedding_model = row.model,
        n.embedding_dim = row.dim,
        n.embedding_ts = row.ts
    """
    tx.run(q, rows=[{"id":i, "vec":v, "model":m, "dim":d, "ts":now_iso()} for i,v,m,d in rows])  # type: ignore

def ensure_vector_index(tx: ManagedTransaction, label: str, dim: int, sim: str="cosine") -> bool:
    name = f"idx_{label}_embedding"
    chk = tx.run("SHOW INDEXES YIELD name WHERE name=$n RETURN name", n=name).single()  # type: ignore
    if chk:
        return False
    q = f"""
    CREATE VECTOR INDEX {name} IF NOT EXISTS
    FOR (n:`{label}`) ON (n.embedding)
    OPTIONS {{ indexConfig: {{ `vector.dimensions`: $dim, `vector.similarity_function`: $sim }} }}
    """
    try:
        tx.run(q, dim=dim, sim=sim)  # type: ignore
    except Neo4jError:
        # 일부 버전에서 파라미터화가 제한적일 수 있으니 즉시 리터럴로 재시도
        q_alt = f"""
        CREATE VECTOR INDEX {name} IF NOT EXISTS
        FOR (n:`{label}`) ON (n.embedding)
        OPTIONS {{ indexConfig: {{ `vector.dimensions`: {int(dim)}, `vector.similarity_function`: '{sim}' }} }}
        """
        tx.run(q_alt)  # type: ignore
    return True

# ---------- Embedding model ----------
class Qwen3Embedder:
    def __init__(self, model_name: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        use_fp16 = torch.cuda.is_available()
        self.model = AutoModel.from_pretrained(model_name, trust_remote_code=True, torch_dtype=torch.float16 if use_fp16 else torch.float32)
        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model_name = model_name
        log.info(f"model={model_name} device={self.device}")

    @torch.no_grad()
    def encode(self, texts: List[str]) -> List[List[float]]:
        texts = [t if t and t.strip() else "[EMPTY]" for t in texts]

        # 텍스트 길이 로깅 (데이터 손실 방지 위해 truncation은 tokenizer에 맡김)
        for i, t in enumerate(texts):
            if len(t) > 10000:
                log.debug(f"Long text detected: idx={i} len={len(t)}")

        tok = self.tokenizer(texts, padding=True, truncation=True, max_length=2048, return_tensors="pt")
        tok = {k:v.to(self.device) for k,v in tok.items()}
        out = self.model(**tok)
        if hasattr(out, "pooler_output") and out.pooler_output is not None:
            emb = out.pooler_output
        else:
            last = out.last_hidden_state
            attn = tok["attention_mask"].unsqueeze(-1)
            emb = (last * attn).sum(dim=1) / attn.sum(dim=1).clamp(min=1)
        emb = torch.nn.functional.normalize(emb, p=2, dim=1)
        return emb.cpu().to(torch.float32).tolist()

    def dim(self) -> int:
        return len(self.encode(["dim-probe"])[0])

    def clear_cache(self):
        """GPU 메모리 캐시 정리"""
        if self.device == "cuda":
            torch.cuda.empty_cache()
            log.debug("GPU cache cleared")

# ---------- main ----------
def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", default=os.getenv("NEO4J_URI"))
    ap.add_argument("--user", default=os.getenv("NEO4J_USER"))
    ap.add_argument("--password", default=os.getenv("NEO4J_PASSWORD"))
    ap.add_argument("--db", default=os.getenv("NEO4J_DATABASE"))
    ap.add_argument("--labels", nargs="*", default=None, help="라벨 목록. 미지정 시 전체 기본 라벨")
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="각 라벨당 상한. 0=전체")
    ap.add_argument("--model", default=os.getenv("EMBED_MODEL"))
    ap.add_argument("--log-level", default=os.getenv("LOG_LEVEL"))
    ap.add_argument("--rel-summary", type=int, default=0, help="각 이웃 라벨당 포함할 관계 요약 수")
    ap.add_argument("--gpu-clear-interval", type=int, default=100, help="GPU 캐시 정리 주기 (배치 단위)")
    args = ap.parse_args()

    # REL_SUMMARY_UPTO를 args로 설정
    global REL_SUMMARY_UPTO
    REL_SUMMARY_UPTO = args.rel_summary

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    log.info("starting embedding job")
    log.info(f"neo4j uri={args.uri} db={args.db}")

    labels = args.labels if args.labels else DEFAULT_LABELS
    log.info(f"labels={labels}")

    drv = None
    emb = None

    try:
        # driver: DB는 세션에서 지정
        drv = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
        emb = Qwen3Embedder(args.model)
        log.info("probing embedding dimension…")
        dim = emb.dim()
        log.info(f"embedding_dim={dim}")

        with drv.session(database=args.db) as ses:
            for label in labels:
                created = ses.execute_write(ensure_vector_index, label, dim)
                log.info(f"vector_index {label}: {'created' if created else 'exists'}")

                result = ses.run(f"MATCH (n:`{label}`) RETURN count(n) AS c").single()  # type: ignore
                total = result["c"] if result else 0
                if args.limit and args.limit < total:
                    total = args.limit
                if total == 0:
                    log.info(f"{label}: no nodes. skip")
                    continue
                log.info(f"{label}: total={total} batch={args.batch}")

                done = 0
                skip = 0
                batch_count = 0
                failed_batches = []
                pbar = tqdm(total=total, desc=label)

                while done < total:
                    need = min(args.batch, total - done)
                    t0 = time.time()

                    try:
                        rows = ses.execute_read(fetch_nodes, label, skip, need)
                        ids = [rid for rid,_ in rows]

                        # REL_SUMMARY_UPTO가 0이면 관계 조회 건너뛰기
                        if REL_SUMMARY_UPTO > 0:
                            relmap = ses.execute_read(fetch_rel_summaries, ids)
                        else:
                            relmap = {}

                        texts = [build_text(label, props, relmap.get(nid, {})) for nid, props in rows]

                        try:
                            vecs = emb.encode(texts)
                        except RuntimeError as e:
                            if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                                log.error(f"{label}: CUDA OOM at batch {batch_count}, batch_size={need}")
                                emb.clear_cache()
                                # 배치 크기를 절반으로 줄여서 재시도
                                if need > 1:
                                    log.info(f"{label}: retrying with smaller batch size={need//2}")
                                    # skip을 유지하고 continue로 재시도
                                    continue
                                else:
                                    log.error(f"{label}: cannot reduce batch size further, skipping batch")
                                    failed_batches.append((skip, skip+need))
                                    skip += need
                                    done += need
                                    pbar.update(need)
                                    continue
                            else:
                                log.error(f"{label}: encode failed batch_size={need} error={e}")
                                raise
                        except Exception as e:
                            log.error(f"{label}: unexpected error during encoding: {e}")
                            failed_batches.append((skip, skip+need))
                            skip += need
                            done += need
                            pbar.update(need)
                            continue

                        valid_payload: List[Tuple[int, List[float], str, int]] = []
                        invalid = 0
                        for (nid,_), vec in zip(rows, vecs):
                            bad = any((x != x) or (x == float('inf')) or (x == float('-inf')) for x in vec)
                            if bad:
                                invalid += 1
                                log.warning(f"{label}: invalid vector for node_id={nid}")
                                continue
                            valid_payload.append((nid, vec, emb.model_name, dim))

                        if invalid:
                            log.warning(f"{label}: invalid_vectors={invalid}/{len(vecs)}")

                        if valid_payload:
                            try:
                                ses.execute_write(set_embeddings, label, valid_payload)
                            except (ServiceUnavailable, SessionExpired) as e:
                                log.error(f"{label}: DB connection error: {e}")
                                log.info(f"{label}: reconnecting...")
                                # 세션이 끊겼으므로 재연결 필요
                                raise
                            except Exception as e:
                                log.error(f"{label}: failed to write embeddings: {e}")
                                failed_batches.append((skip, skip+need))

                        dt = time.time() - t0
                        ips = (len(valid_payload) / dt) if dt > 0 else 0.0
                        done += len(rows)
                        skip += len(rows)
                        batch_count += 1

                        # 진척도 바 업데이트 (상세 정보 표시)
                        pbar.set_postfix({
                            'batch': batch_count,
                            'speed': f'{ips:.1f}n/s',
                            'valid': len(valid_payload)
                        })
                        pbar.update(len(rows))

                        log.info(f"{label}: +{len(valid_payload)} in {dt:.2f}s ({ips:.1f} n/s) progress={done}/{total}")

                        # 주기적으로 GPU 캐시 정리
                        if batch_count % args.gpu_clear_interval == 0:
                            emb.clear_cache()

                    except (ServiceUnavailable, SessionExpired) as e:
                        log.error(f"{label}: connection lost, will retry from current position")
                        time.sleep(5)
                        continue
                    except KeyboardInterrupt:
                        log.warning(f"{label}: interrupted by user at progress={done}/{total}")
                        pbar.close()
                        raise
                    except Exception as e:
                        log.error(f"{label}: unexpected error in batch processing: {e}")
                        failed_batches.append((skip, skip+need))
                        skip += need
                        done += need
                        pbar.update(need)

                pbar.close()

                if failed_batches:
                    log.warning(f"{label}: {len(failed_batches)} batches failed: {failed_batches}")
                else:
                    log.info(f"{label}: all batches completed successfully")

        log.info("done.")

    except KeyboardInterrupt:
        log.warning("Job interrupted by user")
    except Exception as e:
        log.error(f"Fatal error: {e}")
        raise
    finally:
        if drv:
            drv.close()
            log.info("Neo4j driver closed")
        if emb:
            emb.clear_cache()
            log.info("GPU cache cleared")

if __name__ == "__main__":
    main()

