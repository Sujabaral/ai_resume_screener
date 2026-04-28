import re
import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer, util
    SEMANTIC_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    SEMANTIC_MODEL = None


SKILL_ALIASES = {
    "js": "javascript",
    "reactjs": "react",
    "nodejs": "node",
    "postgres": "postgresql",
    "postgre sql": "postgresql",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "gen ai": "generative ai",
    "excel": "microsoft excel",
    "ms excel": "microsoft excel",
    "communication": "communication skills",
    "teamwork": "team collaboration",
}


DEGREE_LEVELS = {
    "phd": 5,
    "doctorate": 5,
    "master": 4,
    "msc": 4,
    "mba": 4,
    "bachelor": 3,
    "bsc": 3,
    "be": 3,
    "b.e": 3,
    "btech": 3,
    "undergraduate": 2,
    "diploma": 1,
    "plus two": 1,
    "+2": 1,
}


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#.\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_skill(skill):
    skill = normalize_text(skill)
    return SKILL_ALIASES.get(skill, skill)


def split_items(raw):
    if not raw:
        return []

    items = re.split(r",|\n|;", raw)
    cleaned = []

    for item in items:
        item = normalize_skill(item.strip())
        if item and item not in cleaned:
            cleaned.append(item)

    return cleaned


def contains_skill(cv_text, skill):
    cv_text = normalize_text(cv_text)
    skill = normalize_skill(skill)

    pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"

    if re.search(pattern, cv_text):
        return True

    # fallback for multi-word or alias-like skill
    words = skill.split()
    if len(words) > 1:
        return all(word in cv_text for word in words)

    return False


def skill_analysis(cv_text, required_skills, preferred_skills):
    matched_required = []
    missing_required = []
    matched_preferred = []
    missing_preferred = []

    for skill in required_skills:
        if contains_skill(cv_text, skill):
            matched_required.append(skill)
        else:
            missing_required.append(skill)

    for skill in preferred_skills:
        if contains_skill(cv_text, skill):
            matched_preferred.append(skill)
        else:
            missing_preferred.append(skill)

    required_score = round((len(matched_required) / len(required_skills)) * 100, 2) if required_skills else 100
    preferred_score = round((len(matched_preferred) / len(preferred_skills)) * 100, 2) if preferred_skills else 100

    return {
        "required_score": required_score,
        "preferred_score": preferred_score,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
    }


def extract_experience_years(text):
    text = normalize_text(text)

    patterns = [
        r"(\d+)\+?\s*years?\s*of\s*experience",
        r"(\d+)\+?\s*yrs?\s*of\s*experience",
        r"experience\s*[:\-]?\s*(\d+)\+?\s*years?",
        r"(\d+)\+?\s*years?\s*experience",
    ]

    found = []

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                found.append(int(match))
            except:
                pass

    return max(found) if found else 0


def experience_analysis(candidate_years, required_years):
    if required_years <= 0:
        return 100, "No minimum experience required."

    if candidate_years >= required_years:
        return 100, f"Candidate meets experience requirement: {candidate_years}/{required_years} years."

    score = round((candidate_years / required_years) * 100, 2)
    return score, f"Candidate has {candidate_years}/{required_years} required years."


def detect_degree_level(text):
    text = normalize_text(text)
    found_levels = []

    for degree, level in DEGREE_LEVELS.items():
        if degree in text:
            found_levels.append(level)

    return max(found_levels) if found_levels else 0


def qualification_analysis(cv_text, required_qualification):
    if not required_qualification:
        return 100, "No required qualification provided."

    candidate_level = detect_degree_level(cv_text)
    required_level = detect_degree_level(required_qualification)

    if required_level == 0:
        # keyword fallback
        required_words = normalize_text(required_qualification).split()
        matched = [word for word in required_words if word in normalize_text(cv_text)]
        score = round((len(matched) / len(required_words)) * 100, 2) if required_words else 100
        return score, f"Qualification keyword match: {score}%."

    if candidate_level >= required_level:
        return 100, "Candidate appears to meet required qualification level."

    if candidate_level == 0:
        return 40, "Required qualification not clearly found in CV."

    return 60, "Candidate qualification may be below or unclear compared to requirement."


def tfidf_similarity(cv_text, jd_text):
    if not jd_text:
        return 100

    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        vectors = vectorizer.fit_transform([cv_text, jd_text])
        score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        return round(score * 100, 2)
    except:
        return 0


def semantic_similarity(cv_text, jd_text):
    if not jd_text:
        return 100

    if SEMANTIC_MODEL is None:
        return tfidf_similarity(cv_text, jd_text)

    try:
        cv_emb = SEMANTIC_MODEL.encode(cv_text[:5000], convert_to_tensor=True)
        jd_emb = SEMANTIC_MODEL.encode(jd_text[:5000], convert_to_tensor=True)
        score = util.cos_sim(cv_emb, jd_emb).item()
        return round(max(0, score) * 100, 2)
    except:
        return tfidf_similarity(cv_text, jd_text)


def section_presence_score(cv_text):
    text = normalize_text(cv_text)

    sections = {
        "skills": ["skills", "technical skills", "core skills"],
        "experience": ["experience", "work experience", "employment"],
        "education": ["education", "academic"],
        "projects": ["projects", "project"],
        "certifications": ["certification", "certifications", "training"],
    }

    found = []

    for section, keywords in sections.items():
        if any(keyword in text for keyword in keywords):
            found.append(section)

    score = round((len(found) / len(sections)) * 100, 2)

    return score, found


def calculate_final_score(required_skill_score, preferred_skill_score, exp_score, qual_score, semantic_score, structure_score):
    score = (
        required_skill_score * 0.35 +
        preferred_skill_score * 0.10 +
        exp_score * 0.18 +
        qual_score * 0.15 +
        semantic_score * 0.17 +
        structure_score * 0.05
    )

    return round(score, 2)


def review_label(score):
    if score >= 85:
        return "Strong Match"
    elif score >= 72:
        return "Good Match"
    elif score >= 55:
        return "Needs Review"
    else:
        return "Low Match"


def generate_ai_analysis(candidate_name, score, skill_data, exp_note, qual_note, semantic_score, sections_found):
    strengths = []
    concerns = []

    if skill_data["matched_required"]:
        strengths.append(f"Matched required skills: {', '.join(skill_data['matched_required'])}")

    if skill_data["matched_preferred"]:
        strengths.append(f"Matched preferred skills: {', '.join(skill_data['matched_preferred'])}")

    if semantic_score >= 70:
        strengths.append("CV content is semantically relevant to the job description.")

    if sections_found:
        strengths.append(f"Detected CV sections: {', '.join(sections_found)}")

    if skill_data["missing_required"]:
        concerns.append(f"Missing required skills: {', '.join(skill_data['missing_required'])}")

    if semantic_score < 55:
        concerns.append("Overall CV content has limited similarity with the job description.")

    if "not clearly" in qual_note.lower() or "below" in qual_note.lower():
        concerns.append(qual_note)

    analysis = f"{candidate_name} scored {score}%. "

    if strengths:
        analysis += "Strengths: " + " ".join(strengths) + " "

    if concerns:
        analysis += "Concerns: " + " ".join(concerns) + " "

    analysis += "Final decision should be reviewed by HR, not made automatically."

    return analysis