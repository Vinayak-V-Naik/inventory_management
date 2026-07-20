'''Builds the FAISS index from knowledge_base/*.md.

Run directly to (re)build after editing the policy docs:

    uv run python -m rag.build_index

Chunks each markdown file by "## " section (splitting long sections by
paragraph), embeds with fastembed (BAAI/bge-small-en-v1.5, local ONNX model)
and saves the index + chunk texts to rag/index/.
'''

import os
import pickle

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge_base")
INDEX_DIR     = os.path.join(os.path.dirname(__file__), "index")
INDEX_PATH    = os.path.join(INDEX_DIR, "policy.faiss")
CHUNKS_PATH   = os.path.join(INDEX_DIR, "chunks.pkl")

EMBED_MODEL     = "BAAI/bge-small-en-v1.5"
MAX_CHUNK_CHARS = 1200


def chunk_markdown(text, source):
    '''One chunk per "## " section, long sections split by paragraph.
    The doc title (# line) is prefixed to every chunk for context.'''
    lines = text.splitlines()
    title = next((l.lstrip("# ").strip() for l in lines if l.startswith("# ")), source)

    sections = []
    current  = []
    for line in lines:
        if line.startswith("## "):
            if current:
                sections.append("\n".join(current).strip())
            current = [line]
        elif not line.startswith("# "):
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())

    chunks = []
    for sec in sections:
        if not sec:
            continue
        if len(sec) <= MAX_CHUNK_CHARS:
            parts = [sec]
        else:
            parts, buf = [], ""
            for para in sec.split("\n\n"):
                if buf and len(buf) + len(para) > MAX_CHUNK_CHARS:
                    parts.append(buf.strip())
                    buf = ""
                buf += para + "\n\n"
            if buf.strip():
                parts.append(buf.strip())
        for p in parts:
            chunks.append({"source": source, "title": title, "text": p})
    return chunks


def collect_chunks(knowledge_dir=KNOWLEDGE_DIR):
    chunks = []
    for fname in sorted(os.listdir(knowledge_dir)):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(knowledge_dir, fname), encoding="utf-8") as f:
            chunks.extend(chunk_markdown(f.read(), fname))
    return chunks


def build_index(knowledge_dir=KNOWLEDGE_DIR):
    import faiss
    import numpy as np
    from fastembed import TextEmbedding

    chunks = collect_chunks(knowledge_dir)
    if not chunks:
        raise RuntimeError(f"No .md files found in {knowledge_dir}/")

    embedder = TextEmbedding(EMBED_MODEL)
    vectors  = np.array(list(embedder.embed([c["text"] for c in chunks])), dtype="float32")
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    os.makedirs(INDEX_DIR, exist_ok=True)
    faiss.write_index(index, INDEX_PATH)
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    print(f"Indexed {len(chunks)} chunks from {knowledge_dir}/ -> {INDEX_PATH}")
    return len(chunks)


if __name__ == "__main__":
    build_index()
