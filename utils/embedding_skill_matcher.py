from sentence_transformers import SentenceTransformer, util


model = SentenceTransformer("all-MiniLM-L6-v2")


def semantic_skill_match(required_skills, resume_text, threshold=0.55):
    if not required_skills:
        return {
            "matched": [],
            "missing": [],
            "score": 0
        }

    resume_sentences = [
        line.strip()
        for line in resume_text.splitlines()
        if len(line.strip()) > 4
    ]

    if not resume_sentences:
        return {
            "matched": [],
            "missing": required_skills,
            "score": 0
        }

    skill_embeddings = model.encode(required_skills, convert_to_tensor=True)
    resume_embeddings = model.encode(resume_sentences, convert_to_tensor=True)
    matches = []
    missing = []

    similarity = util.cos_sim(skill_embeddings, resume_embeddings)

    for i, skill in enumerate(required_skills):
        best_score = float(similarity[i].max())

        if best_score >= threshold or skill.lower() in resume_text.lower():
            matches.append(skill)
        else:
            missing.append(skill)

    score = round((len(matches) / len(required_skills)) * 100, 2)

    return {
        "matched": matches,
        "missing": missing,
        "score": score
    }