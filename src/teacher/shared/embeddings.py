# -*- coding: utf-8 -*-
"""
Embedding module using Qwen3-Embedding-0.6B model
Provides text embedding functionality for ClassMate pipeline
"""
from __future__ import annotations
import os
from typing import List, Dict, Any, Union, Optional
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Lazy imports to avoid loading model until needed
_model = None
_tokenizer = None


def _load_model():
    """Lazy load embedding model from EMBED_MODEL env variable"""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    try:
        from transformers import AutoModel, AutoTokenizer
        import torch

        model_name = os.getenv("EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B")
        print(f"[embedding] Loading model: {model_name}...")

        _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

        # Load model without device_map if accelerate is not available
        try:
            _model = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True,
                device_map="auto" if torch.cuda.is_available() else None
            )
        except ValueError:
            # Fallback: Load without device_map (accelerate not installed)
            print("[embedding] Loading without device_map (accelerate not available)")
            _model = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            # Manually move to CPU if no CUDA
            if not torch.cuda.is_available():
                _model = _model.to('cpu')

        _model.eval()

        print(f"[embedding] Model loaded on device: {_model.device if hasattr(_model, 'device') else 'cpu'}")
        return _model, _tokenizer

    except ImportError:
        raise RuntimeError(
            "transformers and torch are required. "
            "Install with: pip install transformers torch sentence-transformers"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load embedding model: {e}")


def embed_text(text: str, max_length: int = 512) -> List[float]:
    """
    Generate embedding for a single text.

    Args:
        text: Input text to embed
        max_length: Maximum token length

    Returns:
        List of float values representing the embedding vector
    """
    if not text or not text.strip():
        # Return zero vector for empty text
        return [0.0] * 1024  # Qwen3-Embedding-0.6B dimension

    model, tokenizer = _load_model()

    try:
        import torch

        # Tokenize
        inputs = tokenizer(
            text,
            max_length=max_length,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )

        # Move to model device
        if hasattr(model, 'device'):
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

        # Generate embedding
        with torch.no_grad():
            outputs = model(**inputs)
            # Use [CLS] token embedding or mean pooling
            if hasattr(outputs, 'last_hidden_state'):
                embedding = outputs.last_hidden_state[:, 0, :].squeeze()  # [CLS] token
            else:
                embedding = outputs[0][:, 0, :].squeeze()

        # Convert to list
        embedding_list = embedding.cpu().numpy().tolist()
        return embedding_list

    except Exception as e:
        print(f"[embedding] Error embedding text: {e}")
        # Return zero vector on error
        return [0.0] * 1024


def embed_batch(texts: List[str], max_length: int = 512, batch_size: int = 8) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batches.

    Args:
        texts: List of input texts
        max_length: Maximum token length
        batch_size: Number of texts to process at once

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    model, tokenizer = _load_model()
    embeddings = []

    try:
        import torch

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Tokenize batch
            inputs = tokenizer(
                batch_texts,
                max_length=max_length,
                padding=True,
                truncation=True,
                return_tensors="pt"
            )

            # Move to model device
            if hasattr(model, 'device'):
                inputs = {k: v.to(model.device) for k, v in inputs.items()}

            # Generate embeddings
            with torch.no_grad():
                outputs = model(**inputs)
                if hasattr(outputs, 'last_hidden_state'):
                    batch_embeddings = outputs.last_hidden_state[:, 0, :]  # [CLS] tokens
                else:
                    batch_embeddings = outputs[0][:, 0, :]

            # Convert to list
            batch_embeddings_list = batch_embeddings.cpu().numpy().tolist()
            embeddings.extend(batch_embeddings_list)

            print(f"[embedding] Processed batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")

    except Exception as e:
        print(f"[embedding] Error in batch embedding: {e}")
        # Return zero vectors on error
        embeddings = [[0.0] * 1024 for _ in texts]

    return embeddings


def embed_problem(problem: Dict[str, Any]) -> Dict[str, List[float]]:
    """
    Generate embeddings for all relevant fields in a problem.

    Args:
        problem: Problem dictionary from problems.json

    Returns:
        Dictionary with embedding vectors for different fields
    """
    embeddings = {}

    # Embed stem (question text)
    stem = problem.get("stem", "")
    if stem:
        embeddings["stem_embedding"] = embed_text(stem)

    # Embed options (concatenated)
    options = problem.get("options", [])
    if options:
        options_text = " | ".join(str(opt) for opt in options)
        embeddings["options_embedding"] = embed_text(options_text)

    # Embed rationale (explanation)
    rationale = problem.get("rationale", "")
    if rationale:
        embeddings["rationale_embedding"] = embed_text(rationale, max_length=1024)

    # Embed combined context (stem + answer)
    answer = problem.get("answer", "")
    combined = f"{stem} Answer: {answer}"
    embeddings["combined_embedding"] = embed_text(combined)

    return embeddings


def create_searchable_embedding(problem: Dict[str, Any]) -> List[float]:
    """
    Create a single representative embedding for similarity search.
    Combines stem, options, and metadata into one embedding.

    Args:
        problem: Problem dictionary

    Returns:
        Single embedding vector for search
    """
    # Combine key information
    stem = problem.get("stem", "")
    options = problem.get("options", [])
    options_text = " ".join(str(opt) for opt in options) if options else ""
    area = problem.get("area", "")
    difficulty = problem.get("difficulty", "")

    # Create rich context for embedding
    search_text = f"[{area}] [난이도 {difficulty}] {stem} {options_text}"

    return embed_text(search_text, max_length=512)


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Compute cosine similarity between two embeddings.

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector

    Returns:
        Similarity score between -1 and 1
    """
    try:
        import numpy as np

        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    except Exception as e:
        print(f"[embedding] Error computing similarity: {e}")
        return 0.0


def test_embedding():
    """Test embedding functionality"""
    print("=== Testing Qwen Embedding Model ===")

    test_texts = [
        "다음을 듣고, 여자가 하는 말의 목적으로 가장 적절한 것을 고르시오.",
        "What is the main idea of the passage?",
        "다음 표를 보면서 대화를 듣고, 여자가 구입할 스포츠 가방을 고르시오."
    ]

    print("\n1. Single text embedding:")
    emb = embed_text(test_texts[0])
    print(f"   Embedding dimension: {len(emb)}")
    print(f"   First 5 values: {emb[:5]}")

    print("\n2. Batch embedding:")
    embs = embed_batch(test_texts, batch_size=2)
    print(f"   Generated {len(embs)} embeddings")

    print("\n3. Similarity test:")
    sim = compute_similarity(embs[0], embs[2])
    print(f"   Similarity between Korean questions: {sim:.4f}")

    sim_en = compute_similarity(embs[1], embs[0])
    print(f"   Similarity between Korean and English: {sim_en:.4f}")

    print("\n✅ Embedding test completed!")


if __name__ == "__main__":
    test_embedding()
