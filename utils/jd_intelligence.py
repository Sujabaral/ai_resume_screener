import re


SKILL_SEPARATORS = r"[,;/\n|]+"


def clean_skill(skill):
    return skill.strip().lower().replace(".", "").replace("(", "").replace(")", "")


def split_skills(text):
    if not text:
        return []

    raw = re.split(SKILL_SEPARATORS, text)
    skills = []

    for item in raw:
        skill = clean_skill(item)
        if 2 <= len(skill) <= 40:
            skills.append(skill)

    return sorted(set(skills))


def extract_years_required(text, manual_years=0):
    text = text.lower()
    patterns = [
        r"(\d+)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience",
        r"minimum\s+(\d+)\+?\s*(?:years|yrs)",
        r"at least\s+(\d+)\+?\s*(?:years|yrs)",
    ]

    found = []

    for pattern in patterns:
        for match in re.findall(pattern, text):
            found.append(int(match))

    return max(found) if found else int(manual_years or 0)


def extract_responsibilities(text):
    lines = [line.strip("•-* ").strip() for line in text.splitlines() if line.strip()]
    responsibilities = []

    keywords = [
        "develop", "design", "build", "maintain", "implement",
        "manage", "analyze", "collaborate", "test", "deploy",
        "integrate", "optimize", "support"
    ]

    for line in lines:
        lower = line.lower()
        if any(word in lower for word in keywords) and len(line.split()) >= 4:
            responsibilities.append(line)

    return responsibilities[:12]


def extract_skills_from_jd_text(text):
    skill_patterns = [
        r"(?:skills required|required skills|technical skills|must have)[:\-]\s*(.+)",
        r"(?:experience with|knowledge of|proficient in|familiar with|hands on experience in)\s+(.+)",
    ]

    skills = []

    for pattern in skill_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            skills.extend(split_skills(match))

    return sorted(set(skills))


def extract_dynamic_jd_requirements(
    job_description,
    manual_required="",
    manual_preferred="",
    manual_years=0,
    manual_qualification=""
):
    jd_text = job_description or ""

    required_skills = set(split_skills(manual_required))
    preferred_skills = set(split_skills(manual_preferred))

    dynamic_skills = extract_skills_from_jd_text(jd_text)
    required_skills.update(dynamic_skills)

    responsibilities = extract_responsibilities(jd_text)
    required_years = extract_years_required(jd_text, manual_years)

    return {
    "clean_jd": jd_text,
    "job_description": jd_text,

    "required_skills": sorted(required_skills),
    "preferred_skills": sorted(preferred_skills),

    "responsibilities": responsibilities,

    "required_years": required_years,
    "manual_years": required_years,

    "qualification": manual_qualification,
    "required_qualification": manual_qualification,
}