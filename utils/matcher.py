import re


def clean_list(raw_text):
    if not raw_text:
        return []

    items = re.split(r',|\n', raw_text)

    return [
        item.strip().lower()
        for item in items
        if item.strip()
    ]


def skill_match_score(cv_text, required_skills, preferred_skills):
    cv_text = cv_text.lower()

    matched_required = []
    missing_required = []

    for skill in required_skills:
        if skill in cv_text:
            matched_required.append(skill)
        else:
            missing_required.append(skill)

    matched_preferred = []

    for skill in preferred_skills:
        if skill in cv_text:
            matched_preferred.append(skill)

    required_score = (
        len(matched_required) / len(required_skills) * 100
        if required_skills else 100
    )

    preferred_score = (
        len(matched_preferred) / len(preferred_skills) * 100
        if preferred_skills else 100
    )

    return required_score, preferred_score, matched_required, missing_required, matched_preferred


def experience_score(candidate_years, required_years):
    if required_years <= 0:
        return 100

    if candidate_years >= required_years:
        return 100

    return round((candidate_years / required_years) * 100, 2)


def qualification_score(cv_text, qualification):
    if not qualification:
        return 100

    cv_text = cv_text.lower()
    qualification = qualification.lower()

    qualification_keywords = qualification.split()

    matched = sum(1 for word in qualification_keywords if word in cv_text)

    if not qualification_keywords:
        return 100

    return round((matched / len(qualification_keywords)) * 100, 2)


def jd_similarity_score(cv_text, job_description):
    if not job_description:
        return 100

    cv_words = set(cv_text.lower().split())
    jd_words = set(job_description.lower().split())

    if not jd_words:
        return 100

    common = cv_words.intersection(jd_words)

    return round((len(common) / len(jd_words)) * 100, 2)


def final_score(required_score, preferred_score, exp_score, qual_score, semantic_score):
    score = (
        required_score * 0.35 +
        preferred_score * 0.15 +
        exp_score * 0.20 +
        qual_score * 0.15 +
        semantic_score * 0.15
    )

    return round(score, 2)


def recommendation(score):
    if score >= 80:
        return "Accepted"
    elif score >= 60:
        return "Maybe Review"
    else:
        return "Rejected"


def generate_reason(name, score, matched_required, missing_required, candidate_years, required_years):
    if score >= 80:
        return f"{name} is a strong match with good skill coverage and relevant experience."

    if score >= 60:
        return f"{name} partially matches the role but needs manual review. Missing skills: {', '.join(missing_required) if missing_required else 'None'}."

    return f"{name} has a low match score. Missing important skills: {', '.join(missing_required) if missing_required else 'Not clear from CV'}."