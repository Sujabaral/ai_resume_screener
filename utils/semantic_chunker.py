from sentence_transformers import SentenceTransformer, util


model = SentenceTransformer("all-MiniLM-L6-v2")


def chunk_text(text, max_words=120):
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        if len(chunk.split()) > 20:
            chunks.append(chunk)

    return chunks


def best_semantic_match_score(resume_text, jd_text):
    resume_chunks = chunk_text(resume_text)
    jd_chunks = chunk_text(jd_text)

    if not resume_chunks or not jd_chunks:
        return 0

    resume_embeddings = model.encode(resume_chunks, convert_to_tensor=True)
    jd_embeddings = model.encode(jd_chunks, convert_to_tensor=True)

    similarity_matrix = util.cos_sim(jd_embeddings, resume_embeddings)

    best_scores = similarity_matrix.max(dim=1).values

    final_score = float(best_scores.mean() * 100)

    return round(final_score, 2)