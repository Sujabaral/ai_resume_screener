import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.semantic_chunker import best_semantic_match_score
from utils.experience_parser import extract_candidate_years

try:
    from sentence_transformers import SentenceTransformer, util
    MODEL = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    MODEL = None


# --------------------------------------------------
# Basic text helpers
# --------------------------------------------------

def clean(text):
    text = text or ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_term(text, term):
    text = clean(text)
    term = clean(term)

    if not term:
        return False

    pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"

    if re.search(pattern, text):
        return True

    words = term.split()

    if len(words) > 1:
        return all(word in text for word in words)

    return False


def extract_sections(text):
    headings = [
        "summary", "profile", "professional summary",
        "skills", "technical skills", "core skills",
        "experience", "work experience", "employment",
        "professional experience",
        "education", "projects", "certifications", "training"
    ]

    sections = {"general": ""}
    current = "general"

    for line in (text or "").splitlines():
        line = line.strip()

        if not line:
            continue

        lower = line.lower().replace(":", "").strip()

        if lower in headings:
            current = lower
            sections[current] = ""
        else:
            sections[current] = sections.get(current, "") + " " + line

    return sections


# --------------------------------------------------
# Similarity
# --------------------------------------------------

def tfidf_similarity(a, b):
    if not a or not b:
        return 0

    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([a, b])
        return round(cosine_similarity(matrix[0:1], matrix[1:2])[0][0] * 100, 2)
    except Exception:
        return 0


def bert_similarity(a, b):
    if not a or not b:
        return 0

    if MODEL is None:
        return tfidf_similarity(a, b)

    try:
        emb_a = MODEL.encode(a[:7000], convert_to_tensor=True)
        emb_b = MODEL.encode(b[:7000], convert_to_tensor=True)

        score = util.cos_sim(emb_a, emb_b).item()
        raw = max(0, score) * 100

        calibrated = min(100, raw * 1.15)

        return round(calibrated, 2)

    except Exception:
        return tfidf_similarity(a, b)


# --------------------------------------------------
# Semantic skill and domain helpers
# --------------------------------------------------

def semantic_skill_match(cv_text, skill, threshold=55):
    if not cv_text or not skill:
        return False, 0

    context = (
        f"Hands-on experience with {skill}. "
        f"Practical projects using {skill}. "
        f"Professional knowledge of {skill}."
    )

    score = bert_similarity(cv_text[:5000], context)
    return score >= threshold, score


def domain_match_score(cv_text, domain):
    if not cv_text or not domain:
        return 0

    context = f"This resume belongs to a {domain} domain professional."
    return bert_similarity(cv_text[:5000], context)


# --------------------------------------------------
# Skill evidence
# --------------------------------------------------

def smoothed_required_score(points, max_total, matched_count, total_count):
    if total_count <= 0:
        return 100

    raw = (points / max_total) * 100 if max_total else 0
    coverage = matched_count / total_count

    if total_count <= 2:
        coverage_score = 55 + coverage * 40
    elif total_count <= 5:
        coverage_score = 45 + coverage * 50
    else:
        coverage_score = coverage * 100

    final = raw * 0.60 + coverage_score * 0.40

    return round(min(100, final), 2)


def skill_evidence(cv_text, required_skills, preferred_skills):
    required_skills = required_skills or []
    preferred_skills = preferred_skills or []

    sections = extract_sections(cv_text)

    skills_text = (
        sections.get("skills", "") + " " +
        sections.get("technical skills", "") + " " +
        sections.get("core skills", "")
    )

    exp_text = (
        sections.get("experience", "") + " " +
        sections.get("work experience", "") + " " +
        sections.get("professional experience", "") + " " +
        sections.get("employment", "")
    )

    project_text = sections.get("projects", "")

    matched_required = []
    missing_required = []
    evidence_rows = []

    total_points = 0
    max_total = max(len(required_skills), 1) * 10

    for skill in required_skills:
        points = 0
        found_in = []

        if contains_term(skills_text, skill):
            points += 3
            found_in.append("skills section")

        if contains_term(exp_text, skill):
            points += 4
            found_in.append("experience section")

        if contains_term(project_text, skill):
            points += 3
            found_in.append("project section")

        if points == 0 and contains_term(cv_text, skill):
            points += 3
            found_in.append("general CV text")

        if points == 0:
            semantic_found, semantic_score = semantic_skill_match(cv_text, skill)

            if semantic_found:
                points += 4
                found_in.append(f"semantic evidence ({semantic_score}%)")

        points = min(points, 10)

        if points > 0:
            matched_required.append(skill)
        else:
            missing_required.append(skill)

        total_points += points

        evidence_rows.append({
            "skill": skill,
            "required": "Yes",
            "present": "Yes" if points > 0 else "No",
            "found_in": ", ".join(found_in) if found_in else "Not found",
            "evidence_score": points
        })

    matched_preferred = []
    missing_preferred = []
    preferred_total = 0
    preferred_max = max(len(preferred_skills), 1) * 5

    for skill in preferred_skills:
        if contains_term(cv_text, skill):
            matched_preferred.append(skill)
            preferred_total += 5
        else:
            semantic_found, semantic_score = semantic_skill_match(
                cv_text,
                skill,
                threshold=58
            )

            if semantic_found:
                matched_preferred.append(skill)
                preferred_total += 4
            else:
                missing_preferred.append(skill)

    required_score = smoothed_required_score(
        total_points,
        max_total,
        len(matched_required),
        len(required_skills)
    )

    preferred_score = (
        round((preferred_total / preferred_max) * 100, 2)
        if preferred_skills else 100
    )

    return {
        "required_score": required_score,
        "preferred_score": preferred_score,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
        "evidence_rows": evidence_rows
    }


# --------------------------------------------------
# Qualification
# --------------------------------------------------

def qualification_score(cv_text, required_qualification):
    if not required_qualification:
        return 100, "No qualification requirement was provided."

    cv = clean(cv_text)
    req = clean(required_qualification)

    levels = {
        "phd": 5,
        "doctorate": 5,
        "master": 4,
        "msc": 4,
        "mba": 4,
        "bachelor": 3,
        "bsc": 3,
        "bs": 3,
        "be": 3,
        "b.e": 3,
        "btech": 3,
        "b.tech": 3,
        "computer engineering": 3,
        "computer science": 3,
        "information technology": 3,
        "software engineering": 3,
        "diploma": 2,
        "+2": 1,
        "plus two": 1,
    }

    candidate_level = 0
    required_level = 0

    for key, value in levels.items():
        if key in cv:
            candidate_level = max(candidate_level, value)
        if key in req:
            required_level = max(required_level, value)

    if required_level and candidate_level >= required_level:
        return 100, f"Candidate qualification appears to meet requirement: {required_qualification}."

    if required_level and candidate_level == 0:
        return 55, f"Required qualification not clearly found: {required_qualification}."

    if required_level and candidate_level < required_level:
        return 70, f"Candidate qualification may be below requirement: {required_qualification}."

    words = req.split()
    matched = [word for word in words if word in cv]
    score = round((len(matched) / max(len(words), 1)) * 100, 2)

    return score, f"Qualification keyword match is {score}% for: {required_qualification}."


# --------------------------------------------------
# Structure
# --------------------------------------------------

def structure_score(cv_text):
    sections = extract_sections(cv_text)

    important = [
        "skills", "technical skills", "core skills",
        "experience", "work experience", "professional experience",
        "education", "projects"
    ]

    found = [s for s in important if len(sections.get(s, "").strip()) > 20]

    score = min(100, round((len(found) / 6) * 100, 2))

    return score, found


# --------------------------------------------------
# Experience
# --------------------------------------------------

def calculate_experience_score(candidate_years, required_years):
    candidate_years = float(candidate_years or 0)
    required_years = float(required_years or 0)

    if required_years <= 0:
        return 100

    if candidate_years <= 0:
        return 45

    ratio = candidate_years / required_years

    if ratio >= 1.5:
        score = 95
    elif ratio >= 1:
        score = 85 + ((ratio - 1) * 10)
    elif ratio >= 0.7:
        score = 60 + (ratio * 30)
    else:
        score = 40 + (ratio * 20)

    return round(max(0, min(100, score)), 2)


# --------------------------------------------------
# Penalty + Labels
# --------------------------------------------------

def missing_penalty(missing, required):
    if not required:
        return 0

    ratio = len(missing) / len(required)

    if ratio >= 0.75:
        return 12
    if ratio >= 0.50:
        return 8
    if ratio >= 0.30:
        return 5

    return 2 if missing else 0


def score_level(score):
    score = float(score or 0)

    if score < 50:
        return "low"
    elif score < 75:
        return "mid"
    return "high"


def score_label(score, name="Match"):
    score = float(score or 0)

    if score >= 85:
        return f"Excellent {name}"
    elif score >= 75:
        return f"Strong {name}"
    elif score >= 60:
        return f"Good {name}"
    elif score >= 45:
        return f"Average {name}"
    return f"Low {name}"


def get_confidence_level(overall, semantic_score, required_missing_count):
    if overall >= 80 and semantic_score >= 60 and required_missing_count <= 1:
        return "High"
    elif overall >= 60 and semantic_score >= 45:
        return "Medium"
    return "Low"


def get_hr_recommendation(overall, missing_required, experience_score):
    if overall >= 80 and len(missing_required) <= 1 and experience_score >= 70:
        return "Recommended for Interview"
    elif overall >= 60:
        return "Consider for Interview"
    return "Needs Manual Review"


# --------------------------------------------------
# Deep Analysis
# --------------------------------------------------

def build_deep_analysis(data):
    confidence = get_confidence_level(
        data["overall_score"],
        data["semantic_score"],
        len(data["missing_required"])
    )

    recommendation = get_hr_recommendation(
        data["overall_score"],
        data["missing_required"],
        data["experience_score"]
    )

    rank_text = data.get("rank_text") or (
        f"#{data['rank']} out of {data['total_candidates']}"
        if data.get("rank") and data.get("total_candidates")
        else "Ranking will be assigned after all resumes are processed."
    )

    strengths = []
    risks = []

    if data["skill_required_score"] >= 75:
        strengths.append("Strong required-skill coverage.")
    elif data["skill_required_score"] >= 55:
        strengths.append("Moderate required-skill coverage.")
    else:
        risks.append("Several required skills are missing or not clearly proven.")

    if data["semantic_score"] >= 70:
        strengths.append("Resume meaning is strongly aligned with the job description.")
    elif data["semantic_score"] < 45:
        risks.append("Resume content does not strongly match the job description meaning.")

    if data["responsibility_score"] >= 70:
        strengths.append("Candidate work/projects match the job responsibilities well.")
    elif data["responsibility_score"] < 45:
        risks.append("Job responsibility evidence is weak or unclear.")

    if data["required_years"] == 0:
        strengths.append("No strict experience requirement was provided.")
    elif data["candidate_years"] >= data["required_years"]:
        strengths.append("Candidate appears to meet the required experience.")
    else:
        risks.append("Candidate experience appears below the required level.")

    if data["domain_score"] >= 65:
        strengths.append("Candidate profile appears aligned with the job domain.")
    elif data["domain_score"] > 0 and data["domain_score"] < 45:
        risks.append("Candidate domain alignment appears weak.")

    if data["project_score"] >= 65:
        strengths.append("Relevant project experience is detected.")

    if data["education_score"] >= 70:
        strengths.append("Education background appears suitable.")

    return f"""
AI Analysis Summary

Batch Ranking:
This candidate is ranked {rank_text} in this uploaded batch.

Overall Match:
{data['overall_score']}%

Recommendation:
{recommendation}

Confidence Level:
{confidence}

Why this candidate received this score:
- Required skills score: {data['skill_required_score']}%
- Semantic JD-CV match: {data['semantic_score']}%
- Responsibility fit: {data['responsibility_score']}%
- Experience match: {data['experience_score']}%
- Education match: {data['education_score']}%
- Project relevance: {data['project_score']}%
- Resume structure quality: {data['structure_score']}%
- Domain alignment: {data['domain_score']}%

Required Skills Found:
{', '.join(data['matched_required']) if data['matched_required'] else 'No required skills clearly found.'}

Critical Missing Skills:
{', '.join(data['missing_required']) if data['missing_required'] else 'No critical required skills missing.'}

Preferred Skills Found:
{', '.join(data['matched_preferred']) if data['matched_preferred'] else 'No preferred skills clearly found.'}

Preferred Skills Missing:
{', '.join(data['missing_preferred']) if data['missing_preferred'] else 'No preferred skills missing.'}

Experience Analysis:
Required experience: {data['required_years']} years
Candidate experience detected: {data['candidate_years']} years
Status: {'Meets requirement' if data['candidate_years'] >= data['required_years'] else 'Does not clearly meet requirement'}

Education Analysis:
{data['education_note']}

Responsibility Analysis:
The system compared the job responsibilities with the candidate resume using semantic similarity.
Responsibility fit score: {data['responsibility_score']}%

Strengths:
{chr(10).join('- ' + item for item in strengths) if strengths else '- No strong evidence detected.'}

Areas of Improvement / Risk:
{chr(10).join('- ' + item for item in risks) if risks else '- No major risk detected.'}

HR Note:
This is an AI-assisted screening result only. Final hiring decisions should be made by HR.
""".strip()


# --------------------------------------------------
# Main scorer
# --------------------------------------------------

def rank_candidate(cv_text, jd_data):
    jd_data = jd_data or {}

    # v4 compatibility: app.py may send structured CV data as dict
    if isinstance(cv_text, dict):
        cv_data = cv_text

        full_text = cv_data.get("full_text", "") or ""

        structured_text = " ".join([
            cv_data.get("summary_text", ""),
            cv_data.get("skills_text", ""),
            cv_data.get("experience_text", ""),
            cv_data.get("projects_text", ""),
            cv_data.get("education_text", ""),
            cv_data.get("certifications_text", ""),
            cv_data.get("general_text", ""),
        ]).strip()

        cv_text = structured_text if structured_text else full_text

        if full_text and full_text not in cv_text:
            cv_text = cv_text + "\n" + full_text
    else:
        cv_text = cv_text or ""

    # REQUIRED FIX: these variables were missing
    required_skills = jd_data.get("required_skills", []) or []
    preferred_skills = jd_data.get("preferred_skills", []) or []

    required_years = float(jd_data.get("required_years", 0) or 0)
    required_qualification = jd_data.get("qualification", "") or ""
    domain = jd_data.get("domain", "") or ""

    job_description = (
        jd_data.get("job_description")
        or jd_data.get("description")
        or jd_data.get("clean_jd")
        or ""
    )

    responsibilities = jd_data.get("responsibilities", [])

    if isinstance(responsibilities, list):
        responsibilities_text = " ".join(str(r) for r in responsibilities)
    else:
        responsibilities_text = str(responsibilities or "")

    print("SMART RANKER RUNNING")
    print("CV TEXT LENGTH:", len(cv_text))
    print("REQUIRED SKILLS:", required_skills)
    print("PREFERRED SKILLS:", preferred_skills)
    print("JOB DESCRIPTION LENGTH:", len(job_description))
    print("DOMAIN:", domain)

    skill_data = skill_evidence(cv_text, required_skills, preferred_skills)

    candidate_years = extract_candidate_years(cv_text)
    semantic_score = bert_similarity(cv_text, job_description)

    try:
        responsibility_score = (
            best_semantic_match_score(cv_text, responsibilities_text)
            if responsibilities_text else semantic_score
        )
    except Exception:
        responsibility_score = (
            bert_similarity(cv_text, responsibilities_text)
            if responsibilities_text else semantic_score
        )

    education_score, education_note = qualification_score(
        cv_text,
        required_qualification
    )

    try:
        project_score = (
            best_semantic_match_score(cv_text, job_description)
            if job_description else 0
        )
    except Exception:
        project_score = 0

    structure, sections = structure_score(cv_text)

    experience_score = calculate_experience_score(
        candidate_years,
        required_years
    )

    domain_score = domain_match_score(cv_text, domain)

    penalty = missing_penalty(
        skill_data.get("missing_required", []),
        required_skills
    )

    overall_score = (
        skill_data.get("required_score", 0) * 0.30 +
        semantic_score * 0.18 +
        responsibility_score * 0.15 +
        experience_score * 0.17 +
        education_score * 0.07 +
        project_score * 0.08 +
        structure * 0.03 +
        domain_score * 0.02
    ) - penalty

    preferred_bonus = min(4, skill_data.get("preferred_score", 0) * 0.04)
    overall_score += preferred_bonus

    overall_score = round(max(0, min(100, overall_score)), 2)

    analysis_data = {
        "overall_score": overall_score,
        "semantic_score": semantic_score,
        "responsibility_score": responsibility_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "project_score": project_score,
        "structure_score": structure,
        "domain_score": domain_score,
        "skill_required_score": skill_data.get("required_score", 0),
        "matched_required": skill_data.get("matched_required", []),
        "missing_required": skill_data.get("missing_required", []),
        "matched_preferred": skill_data.get("matched_preferred", []),
        "missing_preferred": skill_data.get("missing_preferred", []),
        "required_years": required_years,
        "candidate_years": candidate_years,
        "education_note": education_note,
    }

    analysis = build_deep_analysis(analysis_data)

    return {
        "overall_score": overall_score,
        "label": score_label(overall_score, "Match"),
        "level": score_level(overall_score),

        "semantic_score": semantic_score,
        "responsibility_score": responsibility_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "project_score": project_score,
        "structure_score": structure,
        "domain_score": domain_score,

        "penalty": penalty,
        "preferred_bonus": preferred_bonus,
        "sections": sections,

        "required_years": required_years,
        "candidate_years": candidate_years,
        "education_note": education_note,

        "skill_data": skill_data,
        "analysis": analysis,
    }