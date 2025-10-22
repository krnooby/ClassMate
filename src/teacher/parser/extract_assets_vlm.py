"""
Extract images and tables using VLM-provided bounding boxes.
No OpenDataLoader dependency needed!
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
import fitz

def load_vlm_results(problems_path: str, figures_path: str, tables_path: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Load VLM parsing results"""
    with open(problems_path, "r", encoding="utf-8") as f:
        problems = json.load(f)
    with open(figures_path, "r", encoding="utf-8") as f:
        figures = json.load(f)
    with open(tables_path, "r", encoding="utf-8") as f:
        tables = json.load(f)
    return problems, figures, tables

def extract_asset_from_bbox(
    pdf_path: str,
    page_num: int,
    bbox_norm: List[float],
    output_path: str,
    dpi: int = 150
) -> bool:
    """
    Extract asset from PDF using normalized bbox coordinates.
    bbox_norm: [x1, y1, x2, y2] where values are 0-1 (relative to page dimensions)
    Returns True if successful.
    """
    if not bbox_norm or len(bbox_norm) != 4:
        print(f"  ⚠ Invalid bbox_norm: {bbox_norm}")
        return False
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        
        # Get page dimensions
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Convert normalized coordinates to actual pixel coordinates
        x1_norm, y1_norm, x2_norm, y2_norm = bbox_norm
        x1 = x1_norm * page_width
        y1 = y1_norm * page_height
        x2 = x2_norm * page_width
        y2 = y2_norm * page_height
        
        # Create bbox for PyMuPDF
        pdf_bbox = [x1, y1, x2, y2]
        
        print(f"  → Page {page_num}: {page_width:.0f}x{page_height:.0f}")
        print(f"  → Normalized bbox: {bbox_norm}")
        print(f"  → Actual bbox: [{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}]")
        
        # Extract region
        pix = page.get_pixmap(clip=pdf_bbox, dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        doc.close()
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        
        print(f"  ✓ Extracted: {img.width}x{img.height} → {output_path}")
        return True
        
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract images and tables using VLM bounding boxes")
    parser.add_argument("exam_id", help="Exam ID (e.g., 2026_09_mock)")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--problems-json", required=True, help="Path to VLM problems.json")
    parser.add_argument("--figures-json", required=True, help="Path to VLM figures.json")
    parser.add_argument("--tables-json", required=True, help="Path to VLM tables.json")
    parser.add_argument("--output-dir", default="output/assets", help="Output directory")
    parser.add_argument("--upload-gcs", action="store_true", help="Upload to GCS")
    parser.add_argument("--gcs-bucket", help="GCS bucket name")
    parser.add_argument("--dpi", type=int, default=150, help="DPI for extraction")
    
    args = parser.parse_args()
    
    # Load VLM results
    print("=== Loading VLM results ===")
    problems, figures, tables = load_vlm_results(
        args.problems_json,
        args.figures_json,
        args.tables_json
    )
    print(f"  Loaded {len(problems)} problems, {len(figures)} figures, {len(tables)} tables")
    
    # Extract figures
    print("\n=== Extracting figures ===")
    extracted_files = []
    
    for fig in figures:
        asset_id = fig.get("asset_id") or fig.get("id")
        problem_id = fig.get("problem_id")
        bbox_norm = fig.get("bbox_norm")
        page_num = fig.get("page", 1)
        
        if not bbox_norm:
            print(f"⚠ Figure {asset_id}: No bbox_norm provided")
            continue
        
        # Get problem number from problem_id
        if problem_id:
            try:
                prob_num = int(problem_id.split('-')[-1])
                filename = f"image_{args.exam_id}-{prob_num:04d}.png"
            except:
                filename = f"image_{args.exam_id}_{asset_id}.png"
        else:
            filename = f"image_{args.exam_id}_{asset_id}.png"
        
        output_path = Path(args.output_dir) / filename
        
        print(f"\nFigure {asset_id} (Problem ID: {problem_id}):")
        if extract_asset_from_bbox(args.pdf, page_num, bbox_norm, str(output_path), args.dpi):
            extracted_files.append(str(output_path))
    
    # Extract tables
    print("\n=== Extracting tables ===")
    
    for tbl in tables:
        table_id = tbl.get("table_id") or tbl.get("id")
        problem_id = tbl.get("problem_id")
        bbox_norm = tbl.get("source", {}).get("bbox_norm") if isinstance(tbl.get("source"), dict) else tbl.get("bbox_norm")
        page_num = tbl.get("source", {}).get("page", 1) if isinstance(tbl.get("source"), dict) else tbl.get("page", 1)
        
        if not bbox_norm:
            print(f"⚠ Table {table_id}: No bbox_norm provided")
            continue
        
        # Get problem number from problem_id
        if problem_id:
            try:
                prob_num = int(problem_id.split('-')[-1])
                filename = f"table_{args.exam_id}-{prob_num:04d}.png"
            except:
                filename = f"table_{args.exam_id}_{table_id}.png"
        else:
            filename = f"table_{args.exam_id}_{table_id}.png"
        
        output_path = Path(args.output_dir) / filename
        
        print(f"\nTable {table_id} (Problem ID: {problem_id}):")
        if extract_asset_from_bbox(args.pdf, page_num, bbox_norm, str(output_path), args.dpi):
            extracted_files.append(str(output_path))
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"  Total extracted: {len(extracted_files)} files")
    
    # Upload to GCS if requested
    if args.upload_gcs and extracted_files:
        print(f"\n=== Uploading to GCS ===")
        
        from dotenv import load_dotenv
        load_dotenv()
        
        import os
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from teacher.gcs_io import upload_public
        
        bucket = args.gcs_bucket or os.getenv('GCS_BUCKET', 'classmate__v1')
        print(f"  Using bucket: {bucket}")
        
        for local_path in extracted_files:
            dest = Path(local_path).name
            try:
                public_url, _ = upload_public(local_path, bucket, dest)
                print(f"  ✓ {dest}: {public_url}")
            except Exception as e:
                print(f"  ✗ {dest}: {e}")

if __name__ == "__main__":
    main()
