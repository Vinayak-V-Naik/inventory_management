'''Loads the FAISS policy index and answers similarity queries.

search(query, k) returns the k most relevant policy chunks. The index is
built automatically on first use if missing (run rag/build_index.py after
editing the knowledge_base docs to refresh it).
'''

import os
import pickle

from rag.build_index import CHUNKS_PATH, EMBED_MODEL, INDEX_PATH, build_index

_state = {"index": None, "chunks": None, "embedder": None}


def _ensure_loaded():
    if _state["index"] is not None:
        return
    import faiss
    from fastembed import TextEmbedding

    if not (os.path.exists(INDEX_PATH) and os.path.exists(CHUNKS_PATH)):
        build_index()

    _state["index"] = faiss.read_index(INDEX_PATH)
    with open(CHUNKS_PATH, "rb") as f:
        _state["chunks"] = pickle.load(f)
    _state["embedder"] = TextEmbedding(EMBED_MODEL)


def search(query, k=4):
    '''Returns up to k chunks: [{"source", "title", "text", "score"}]'''
    import faiss
    import numpy as np

    _ensure_loaded()
    q = np.array(list(_state["embedder"].embed([query])), dtype="float32")
    faiss.normalize_L2(q)
    scores, ids = _state["index"].search(q, k)

    hits = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        chunk = dict(_state["chunks"][idx])
        chunk["score"] = float(score)
        hits.append(chunk)
    return hits
