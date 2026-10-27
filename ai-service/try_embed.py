import math
import time

from app.ingestion.chunker import chunk_sections
from app.ingestion.embedder import EMBEDDING_DIM, MODEL_NAME, embed_texts
from app.ingestion.parsers import ParsedSection


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


print("Loading model (first run downloads about 90 MB)...")
t0 = time.perf_counter()
warmup = embed_texts(["warm up"])
print(f"Model ready in {time.perf_counter() - t0:.1f} s | model: {MODEL_NAME}")
print(f"Vector size: {len(warmup[0])} (expected {EMBEDDING_DIM})")

a, b, c = embed_texts([
    "Vendor spending increased last quarter.",
    "Supplier costs went up over the last three months.",
    "The cat sat on the sofa and slept.",
])
print("\nMeaning similarity (1.0 = same meaning, 0 = unrelated):")
print(f"  vendor spending  vs  supplier costs : {cosine(a, b):.3f}   <- should be higher")
print(f"  vendor spending  vs  cat on sofa     : {cosine(a, c):.3f}   <- should be lower")

long_text = " ".join(
    f"Vendor spending in region {i} rose because of contract number {i}." for i in range(1, 120)
)
chunks = chunk_sections([ParsedSection(long_text, 1)] * 6)
texts = [ch.text for ch in chunks]
t1 = time.perf_counter()
vectors = embed_texts(texts)
elapsed = time.perf_counter() - t1
print(f"\nEmbedded {len(vectors)} chunks in {elapsed:.2f} s ({len(vectors) / elapsed:.1f} chunks/s)")