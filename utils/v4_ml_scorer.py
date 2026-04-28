import math

from utils.smart_ranker import (
    rank_candidate as smart_rank_candidate,
    bert_similarity,
    score_label,
    score_level,
)


def clamp(value, minimum=0, maximum=100):
    try:
        value = float(value or 0)
    except Exception:
        value = 0

    return round(max(minimum, min(maximum, value)), 2)


def safe_get_cv_text(cv_data):
    if isinstance(cv_data, dict):
        return cv_data.get("full_text", "") or ""

    return cv_data or ""


def weighted_confidence(features):
    """
    v4 ML-like confidence model.

    This is not fake random AI.
    It uses multiple learned-style signals:
    - skill evidence
    - semantic match
    - responsibility fit
    - experience fit
    - education fit
    - project relevance
    - structure quality
    - domain alignment
    - penalty risk
    """

    skill = features.get("skill_required_score", 0)
    semantic = features.get("semantic_score", 0)
    responsibility = features.get("responsibility_score", 0)
    experience = features.get("experience_score", 0)
    education = features.get("education_score", 0)
    project = features.get("project_score", 0)
    structure = features.get("structure_score", 0)
    domain = features.get("domain_score", 0)
    penalty = features.get("penalty", 0)

    raw = (
        skill * 0.30 +
        semantic * 0.17 +
        responsibility * 0.16 +
        experience * 0.16 +
        education * 0.07 +
        project * 0.08 +
        structure * 0.03 +
        domain * 0.03
    ) - penalty

    return clamp(raw)


def sigmoid_calibration(score):
    """
    Smooths the score so very weak profiles stay low,
    strong profiles rise naturally, and mid candidates are not overboosted.
    """

    score = clamp(score)
    centered = (score - 60) / 13
    calibrated = 100 / (1 + math.exp(-centered))

    # Blend original + sigmoid to avoid extreme jumps
    final = (score * 0.72) + (calibrated * 0.28)

    return clamp(final)


def section_quality_bonus(cv_data):
    if not isinstance(cv_data, dict):
        return 0

    bonus = 0

    if len(cv_data.get("skills_text", "")) > 50:
        bonus += 1.0

    if len(cv_data.get("experience_text", "")) > 120:
        bonus += 1.2

    if len(cv_data.get("projects_text", "")) > 80:
        bonus += 1.0

    if len(cv_data.get("education_text", "")) > 40:
        bonus += 0.8

    return min(4, bonus)


def domain_consistency_score(cv_text, jd_data):
    domain = jd_data.get("domain", "")

    if not domain:
        return 0

    prompt = f"This resume is strongly related to the {domain} job domain."
    return bert_similarity(cv_text[:5000], prompt)


def seniority_alignment(candidate_years, required_years):
    candidate_years = float(candidate_years or 0)
    required_years = float(required_years or 0)

    if required_years <= 0:
        return 100

    if candidate_years <= 0:
        return 40

    ratio = candidate_years / required_years

    if 0.8 <= ratio <= 1.8:
        return 100

    if ratio < 0.8:
        return clamp(55 + ratio * 35)

    # Very overqualified: not bad, but slightly less ideal for junior roles
    return clamp(95 - min(20, (ratio - 1.8) * 8))


def risk_penalty(rank, skill_data):
    missing_required = skill_data.get("missing_required", [])
    required_score = skill_data.get("required_score", 0)

    penalty = 0

    if required_score < 40:
        penalty += 8

    if len(missing_required) >= 5:
        penalty += 7
    elif len(missing_required) >= 3:
        penalty += 5
    elif len(missing_required) >= 1:
        penalty += 2

    if rank.get("semantic_score", 0) < 35:
        penalty += 5

    if rank.get("experience_score", 0) < 50:
        penalty += 4

    return penalty


def build_v4_analysis(rank, v4_score, ml_confidence, seniority_score, section_bonus):
    skill_data = rank.get("skill_data", {})

    missing_required = skill_data.get("missing_required", [])
    matched_required = skill_data.get("matched_required", [])
    matched_preferred = skill_data.get("matched_preferred", [])

    if v4_score >= 85:
        recommendation = "Highly Recommended for Interview"
        confidence = "High"
    elif v4_score >= 72:
        recommendation = "Recommended for Interview"
        confidence = "High"
    elif v4_score >= 58:
        recommendation = "Consider for Interview"
        confidence = "Medium"
    else:
        recommendation = "Needs Manual Review"
        confidence = "Low"

    strengths = []
    risks = []

    if rank.get("required_skill_score", 0) >= 75 or skill_data.get("required_score", 0) >= 75:
        strengths.append("Strong required-skill evidence was found.")

    if rank.get("semantic_score", 0) >= 65:
        strengths.append("Resume meaning is strongly aligned with the job description.")

    if rank.get("responsibility_score", 0) >= 65:
        strengths.append("Candidate experience/projects are relevant to the listed responsibilities.")

    if seniority_score >= 80:
        strengths.append("Candidate seniority appears suitable for the required experience level.")

    if section_bonus >= 2:
        strengths.append("Resume has useful structured sections for AI analysis.")

    if missing_required:
        risks.append("Some required skills were missing or not clearly proven: " + ", ".join(missing_required[:8]))

    if rank.get("semantic_score", 0) < 45:
        risks.append("Overall JD-to-CV semantic alignment is weak.")

    if rank.get("experience_score", 0) < 55:
        risks.append("Candidate experience may not clearly meet the required years.")

    return f"""
V4 AI/ML Screening Analysis

Final V4 Match Score:
{v4_score}%

Recommendation:
{recommendation}

Model Confidence:
{confidence}

Internal ML Confidence Score:
{ml_confidence}%

Why this score was assigned:
- Required skill evidence: {skill_data.get("required_score", 0)}%
- Preferred skill evidence: {skill_data.get("preferred_score", 0)}%
- Semantic JD-CV match: {rank.get("semantic_score", 0)}%
- Responsibility fit: {rank.get("responsibility_score", 0)}%
- Experience match: {rank.get("experience_score", 0)}%
- Seniority alignment: {seniority_score}%
- Education match: {rank.get("education_score", 0)}%
- Project relevance: {rank.get("project_score", 0)}%
- Resume structure quality: {rank.get("structure_score", 0)}%
- Domain alignment: {rank.get("domain_score", 0)}%
- Section quality bonus: {section_bonus}

Required Skills Found:
{", ".join(matched_required) if matched_required else "No required skills clearly found."}

Critical Missing Skills:
{", ".join(missing_required) if missing_required else "No critical required skills missing."}

Preferred Skills Found:
{", ".join(matched_preferred) if matched_preferred else "No preferred skills clearly found."}

Experience Comparison:
Required experience: {rank.get("required_years", 0)} years
Candidate experience detected: {rank.get("candidate_years", 0)} years

Strengths:
{chr(10).join("- " + s for s in strengths) if strengths else "- No strong evidence detected."}

Risks / Review Points:
{chr(10).join("- " + r for r in risks) if risks else "- No major risk detected."}

HR Note:
This V4 score is AI-assisted. HR should use it for prioritization, not automatic rejection.
""".strip()


def rank_candidate_v4(cv_data, jd_data):
    """
    Main V4 ranking function.

    Input:
    - cv_data: dict from app.py with structured resume sections
    - jd_data: dict from jd_intelligence.py

    Output:
    - same shape as smart_ranker output
    """

    cv_text = safe_get_cv_text(cv_data)

    # Step 1: Get strong base score from existing smart ranker
    try:
        base_rank = smart_rank_candidate(cv_data, jd_data)
    except Exception:
        base_rank = smart_rank_candidate(cv_text, jd_data)

    skill_data = base_rank.get("skill_data", {})

    # Step 2: Add v4-specific signals
    domain_score = base_rank.get("domain_score", 0)

    if not domain_score:
        domain_score = domain_consistency_score(cv_text, jd_data)

    seniority_score = seniority_alignment(
        base_rank.get("candidate_years", 0),
        base_rank.get("required_years", 0),
    )

    section_bonus = section_quality_bonus(cv_data)

    features = {
        "skill_required_score": skill_data.get("required_score", 0),
        "semantic_score": base_rank.get("semantic_score", 0),
        "responsibility_score": base_rank.get("responsibility_score", 0),
        "experience_score": base_rank.get("experience_score", 0),
        "education_score": base_rank.get("education_score", 0),
        "project_score": base_rank.get("project_score", 0),
        "structure_score": base_rank.get("structure_score", 0),
        "domain_score": domain_score,
        "penalty": base_rank.get("penalty", 0),
    }

    ml_confidence = weighted_confidence(features)

    seniority_adjusted = (
        ml_confidence * 0.88 +
        seniority_score * 0.08 +
        section_bonus
    )

    risk = risk_penalty(base_rank, skill_data)

    raw_v4 = seniority_adjusted - risk
    v4_score = sigmoid_calibration(raw_v4)

    # Keep strong hard evidence from being lowered too much
    base_score = base_rank.get("overall_score", 0)

    final_score = clamp((v4_score * 0.72) + (base_score * 0.28))

    base_rank["overall_score"] = final_score
    base_rank["label"] = score_label(final_score, "V4 Match")
    base_rank["level"] = score_level(final_score)

    base_rank["domain_score"] = domain_score
    base_rank["seniority_score"] = seniority_score
    base_rank["ml_confidence"] = ml_confidence
    base_rank["section_bonus"] = section_bonus
    base_rank["v4_score"] = final_score

    base_rank["analysis"] = build_v4_analysis(
        base_rank,
        final_score,
        ml_confidence,
        seniority_score,
        section_bonus,
    )

    return base_rank